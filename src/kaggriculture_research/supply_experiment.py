"""Preregistered information ablation with episode-atomic, verified recovery."""

import copy
import json
import time
from collections import Counter
from collections.abc import Callable
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.environment import (
    engine_manifest,
    game,
    make_environment,
    validate_protocol,
)
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.market_features import market_features
from kaggriculture_research.market_policy import MarketPolicy
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_research.relationship_policy import RelationshipPolicy
from kaggriculture_research.supply_policy import ARMS, SupplyPolicy

KEYS = ("seed", "seat", "opponent", "arm")
OPPONENTS = ("relationship101", "market10")
CONTRASTS = (("visible", "bank"), ("history", "visible"), ("cash", "history"), ("cash", "bank"))
METRICS = ("match_score", "coins", "coin_margin", "discarded_units", "minimum_observed_cash")


def feature_bank(obs: dict, past, candidate: SupplyPolicy) -> tuple[dict, dict]:
    vectors = [observe_features(obs), relationship_features(obs), past, market_features(obs)]
    vectors.extend(candidate.last_features.values())
    values = {k: v for f in vectors for k, v in f.values.items()}
    schema = {k: v for f in vectors for k, v in f.families.items()}
    if len(values) != 1308 or len(values) != sum(len(f.values) for f in vectors):
        raise ValueError("Feature schema or namespace overlap")
    return values, schema


def episode_hash(payload: dict) -> str:
    return digest(
        {
            k: v
            for k, v in payload.items()
            if k
            not in ("latency_ms", "feature_extraction_ms", "execution_seconds", "semantic_sha256")
        }
    )


def run_game(seed: int, seat: int, opponent: str, arm: str, stride: int = 4) -> dict:
    if opponent not in OPPONENTS or seat not in (0, 1) or stride != 4:
        raise ValueError("Unregistered episode design")
    candidate = SupplyPolicy(arm)
    rival = RelationshipPolicy("101") if opponent == "relationship101" else MarketPolicy("10")
    causal = CausalHistory()
    records, latencies, feature_times, samples = [], [], [], []
    columns, schema, count = [], {}, Counter()
    minimum_cash, started = 3000, time.monotonic()

    def instrument(actor, is_candidate):
        def call(observation, configuration):
            nonlocal candidate, schema, columns, minimum_cash
            if configuration.get("seed") is not None:
                raise ValueError("Seed leaked into policy configuration")
            obs = {k: copy.deepcopy(observation[k]) for k in PUBLIC_FIELDS}
            before = copy.deepcopy(obs)
            tick = time.perf_counter()
            action = candidate(obs) if is_candidate else actor(obs)
            elapsed = (time.perf_counter() - tick) * 1000
            if obs != before:
                raise ValueError("Policy mutated its legal observation")
            record = {"player": obs["player"], "observation": before, "action": action}
            if is_candidate:
                latencies.append(elapsed)
                record["diagnostics"] = copy.deepcopy(candidate.last_diagnostics)
                count.update(
                    {
                        f"interventions_{k}": v
                        for k, v in candidate.last_diagnostics["interventions"].items()
                    }
                )
                for name in ("supply_activations", "cash_extra_sale_units"):
                    count[name] += candidate.last_diagnostics[name]
                past = causal.observe(obs)
                if obs["step"] % stride == 0 or obs["step"] == 718:
                    tick = time.perf_counter()
                    values, families = feature_bank(obs, past, candidate)
                    if schema and (schema != families or columns != list(values)):
                        raise ValueError("Feature schema drift")
                    schema, columns = families, list(values)
                    samples.append({"step": obs["step"], "values": list(values.values())})
                    feature_times.append((time.perf_counter() - tick) * 1000)
                farm, private = copy.deepcopy((obs["farms"][seat], obs["private"]))
                minimum_cash = min(minimum_cash, farm["money"])
                for index, command in enumerate([action["farmer"], *action["hands"]]):
                    old = copy.deepcopy((farm, private))
                    carried, shed = (
                        sum(private["inventories"][index].values()),
                        sum(private["shed"].values()),
                    )
                    game._apply_unit_action(farm, private, index, command, 10, obs["day"], 24, 100)
                    count["ineffective_farm_actions"] += int(
                        command[0] != "PASS" and old == (farm, private)
                    )
                    after = sum(private["inventories"][index].values())
                    if command[0] == "HARVEST":
                        count["harvested_units"] += after - carried
                    elif command[0] == "DROP":
                        count["discarded_units"] += (
                            carried - after - (sum(private["shed"].values()) - shed)
                        )
                for order in action["market"]:
                    if order[0] == "SELL":
                        _, item, quantity = order
                        if quantity > private["shed"].get(item, 0):
                            raise ValueError("Sale exceeds observable inventory")
                        private["shed"][item] -= quantity
                        count["sold_units"] += quantity
                    elif order[0] not in ("BUY_SEED", "HIRE"):
                        raise ValueError("Registered crop-only conservation scope changed")
                if obs["hour"] == 23:
                    count["discarded_units"] += max(
                        0,
                        sum(private["shed"].values())
                        + sum(sum(i.values()) for i in private["inventories"])
                        - 100,
                    )
                if obs["step"] % 24 == 0 or obs["step"] == 718:
                    candidate = SupplyPolicy.from_state_dict(candidate.state_dict())
                    count["state_roundtrips"] += 1
            records.append(record)
            return action

        return call

    env = make_environment(seed, {"episodeSteps": 720})
    actors = [instrument(candidate, True), instrument(rival, False)]
    env.run(actors if seat == 0 else list(reversed(actors)))
    statuses, rewards = [s.status for s in env.state], [s.reward for s in env.state]
    if statuses != ["DONE", "DONE"] or len(env.steps) != 720 or len(latencies) != 719:
        raise ValueError("Incomplete official episode")
    terminal = copy.deepcopy(env.state[seat].observation["private"])
    unsold = sum(
        n
        for inv in [terminal["shed"], *terminal["inventories"]]
        for p, n in inv.items()
        if p in game.PRODUCTS
    )
    if count["harvested_units"] != count["sold_units"] + count["discarded_units"] + unsold:
        raise ValueError("Exact product conservation failed")
    summary = {
        "seed": seed,
        "seat": seat,
        "opponent": opponent,
        "arm": arm,
        "match_score": float(rewards[seat] > rewards[1 - seat])
        + 0.5 * (rewards[seat] == rewards[1 - seat]),
        "coins": rewards[seat],
        "coin_margin": rewards[seat] - rewards[1 - seat],
        "minimum_observed_cash": minimum_cash,
        "unsold_product_units": unsold,
        **{
            k: count[k]
            for k in (
                "harvested_units",
                "sold_units",
                "discarded_units",
                "ineffective_farm_actions",
                "interventions_delivery",
                "interventions_market_timing",
                "supply_activations",
                "cash_extra_sale_units",
                "state_roundtrips",
            )
        },
    }
    payload = {
        "summary": summary,
        "records": records,
        "states": 720,
        "statuses": statuses,
        "evaluator_terminal_private": terminal,
        "rewards": rewards,
        "feature_columns": columns,
        "feature_schema": schema,
        "feature_samples": samples,
        "latency_ms": latencies,
        "feature_extraction_ms": feature_times,
        "execution_seconds": time.monotonic() - started,
    }
    payload["semantic_sha256"] = episode_hash(payload)
    validate_episode(payload, {k: summary[k] for k in KEYS})
    return payload


def validate_episode(payload: dict, key: dict) -> None:
    if {k: payload["summary"][k] for k in KEYS} != key:
        raise ValueError("Checkpoint job identity differs")
    if payload["semantic_sha256"] != episode_hash(payload):
        raise ValueError("Checkpoint semantic identity differs")
    if payload["states"] != 720 or payload["statuses"] != ["DONE", "DONE"]:
        raise ValueError("Checkpoint episode incomplete")
    for who in (0, 1):
        if [r["observation"]["step"] for r in payload["records"] if r["player"] == who] != list(
            range(719)
        ):
            raise ValueError("Checkpoint callback sequence differs")
    if [s["step"] for s in payload["feature_samples"]] != [*range(0, 719, 4), 718]:
        raise ValueError("Checkpoint sample sequence differs")
    if (
        len(payload["feature_columns"]) != 1308
        or len(set(payload["feature_columns"])) != 1308
        or set(payload["feature_columns"]) != set(payload["feature_schema"])
    ):
        raise ValueError("Checkpoint feature schema differs")
    for sample in payload["feature_samples"]:
        if len(sample["values"]) != 1308 or not np.isfinite(sample["values"]).all():
            raise ValueError("Invalid checkpoint feature vector")
    row = payload["summary"]
    rewards, seat = payload["rewards"], row["seat"]
    margin = rewards[seat] - rewards[1 - seat]
    if (
        row["coins"] != rewards[seat]
        or row["coin_margin"] != margin
        or row["match_score"] != float(margin > 0) + 0.5 * (margin == 0)
    ):
        raise ValueError("Checkpoint outcome inconsistent")
    if (
        row["harvested_units"]
        != row["sold_units"] + row["discarded_units"] + row["unsold_product_units"]
    ):
        raise ValueError("Checkpoint conservation inconsistent")


def common_lineage(root: Path, protocol: dict) -> dict:
    foundation = json.loads((root / "configs/research.json").read_text())
    previous = json.loads((root / "configs/market_research.json").read_text())
    validate_protocol(foundation)
    forbidden = set(
        foundation["development_seeds"]
        + foundation["validation_seeds"]
        + foundation["holdout_seeds"]
        + previous["development_seeds"]
    )
    if set(protocol["development_seeds"]) & forbidden:
        raise ValueError("Previously used or reserved seed entered the new development study")
    expected = {
        "development_seeds": [1301, 1302, 1303, 1304],
        "seats": [0, 1],
        "configuration": {"episodeSteps": 720},
        "arms": list(ARMS),
        "opponents": list(OPPONENTS),
        "contrasts": [list(c) for c in CONTRASTS],
        "max_games": 64,
        "maximum_hold_actions": 4,
        "rival_scenario_weight": 0.5,
        "feature_sample_stride": 4,
        "max_new_games_per_batch": 8,
        "max_seconds_per_batch": 240,
        "primary_metric": "match_score",
        "bootstrap_resamples": 4000,
        "bootstrap_seed": 3301,
    }
    if any(protocol.get(k) != v for k, v in expected.items()):
        raise ValueError("Registered supply design changed")
    old_path = root / "reports/market_research.json"
    if file_digest(old_path) != protocol["frozen_market_report_sha256"]:
        raise ValueError("Frozen market evidence changed")
    source = root / "src/kaggriculture_research"
    old = json.loads(old_path.read_text())
    for name, expected_hash in old["lineage"]["code"].items():
        if file_digest(source / name) != expected_hash:
            raise ValueError(f"Frozen source changed: {name}")
    if file_digest(source / "market_history.py") != protocol["frozen_market_history_sha256"]:
        raise ValueError("Frozen market-history source changed")
    return {
        "engine": engine_manifest(),
        "protocol": protocol,
        "code": {p.name: file_digest(p) for p in sorted(source.glob("*.py"))},
    }


def job_plan(root: Path, protocol: dict) -> tuple[dict, list[dict]]:
    common = common_lineage(root, protocol)
    jobs = []
    for values in product(
        *(protocol[k] for k in ("development_seeds", "seats", "opponents", "arms"))
    ):
        key = dict(zip(KEYS, values, strict=True))
        lineage = {**common, **key}
        jobs.append(
            {
                "key": key,
                "lineage": lineage,
                "path": "artifacts/supply_episodes/" + digest(lineage) + ".json.gz",
            }
        )
    return common, jobs


def run_batch(
    root: Path,
    protocol: dict,
    progress: Progress,
    checkpoint_ready: Callable[[Path], None] | None = None,
) -> dict:
    common, jobs = job_plan(root, protocol)
    new = reused = 0
    started = time.monotonic()
    manifests = []
    for job in jobs:
        path = root / job["path"]
        payload = load_checkpoint(path, job["lineage"])
        if path.exists() and payload is None:
            raise ValueError("Existing checkpoint has different lineage; do not overwrite")
        if payload is None:
            if (
                new >= protocol["max_new_games_per_batch"]
                or time.monotonic() - started >= protocol["max_seconds_per_batch"]
            ):
                break
            with progress.stage("supply_" + "_".join(map(str, job["key"].values()))):
                payload = run_game(**job["key"], stride=protocol["feature_sample_stride"])
                save_checkpoint(path, job["lineage"], payload)
                new += 1
        else:
            reused += 1
        validate_episode(payload, job["key"])
        if checkpoint_ready:
            checkpoint_ready(path)
        manifests.append(
            {
                **job["key"],
                "path": job["path"],
                "sha256": file_digest(path),
                "semantic_sha256": payload["semantic_sha256"],
            }
        )
    status = {
        "experiment": protocol["experiment"],
        "lineage": common,
        "complete": len(manifests) == len(jobs),
        "completed_games": len(manifests),
        "new_games": new,
        "reused_games": reused,
        "expected_games": len(jobs),
        "artifact_manifest": manifests,
        "feature_completion_gate": "closed",
    }
    write_json(root / "reports/supply_progress.json", status)
    return status


def paired_summary(frame: pd.DataFrame, resamples: int, bootstrap_seed: int) -> pd.DataFrame:
    if frame.duplicated(list(KEYS)).any():
        raise ValueError("Duplicated paired episode")
    for _, group in frame.groupby(["seed", "seat", "opponent"]):
        if set(group.arm) != set(ARMS):
            raise ValueError("Incomplete paired block")
    rng, rows = np.random.default_rng(bootstrap_seed), []
    for scope in ("pooled", *OPPONENTS):
        subset = frame if scope == "pooled" else frame[frame.opponent == scope]
        for treatment, control in CONTRASTS:
            indexed = subset.set_index(["seed", "seat", "opponent", "arm"])
            for metric in METRICS:
                delta = indexed[metric].xs(treatment, level="arm") - indexed[metric].xs(
                    control, level="arm"
                )
                clusters = delta.groupby(level="seed").mean()
                draws = rng.choice(
                    clusters.to_numpy(), size=(resamples, len(clusters)), replace=True
                ).mean(axis=1)
                rows.append(
                    {
                        "opponent": scope,
                        "contrast": treatment + "-" + control,
                        "metric": metric,
                        "effect": float(clusters.mean()),
                        "bootstrap_low": float(np.quantile(draws, 0.025)),
                        "bootstrap_high": float(np.quantile(draws, 0.975)),
                        "seed_clusters": len(clusters),
                        "seed_differences": clusters.to_json(),
                    }
                )
    return pd.DataFrame(rows)


def summarize(root: Path, protocol: dict) -> dict:
    common, jobs = job_plan(root, protocol)
    rows, matrix, metadata, manifests = [], [], [], []
    schema, columns, latency, extraction = {}, [], [], []
    total_seconds = 0.0
    for job in jobs:
        path = root / job["path"]
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Cannot summarize an incomplete study")
        validate_episode(payload, job["key"])
        if schema and (
            schema != payload["feature_schema"] or columns != payload["feature_columns"]
        ):
            raise ValueError("Between-episode feature schema drift")
        schema, columns = payload["feature_schema"], payload["feature_columns"]
        rows.append(payload["summary"])
        latency.extend(payload["latency_ms"])
        extraction.extend(payload["feature_extraction_ms"])
        total_seconds += payload["execution_seconds"]
        for sample in payload["feature_samples"]:
            matrix.append(sample["values"])
            metadata.append({**job["key"], "step": sample["step"]})
        manifests.append(
            {
                **job["key"],
                "path": job["path"],
                "sha256": file_digest(path),
                "semantic_sha256": payload["semantic_sha256"],
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "reports/supply_games.csv", index=False)
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    effects.to_csv(root / "reports/supply_effects.csv", index=False)
    data = pd.DataFrame(matrix, columns=columns)
    distinct = data.nunique()
    constants = distinct[distinct <= 1].index.tolist()
    nonconstant = [n for n in columns if n not in constants]
    duplicates = {}
    for name in nonconstant:
        duplicates.setdefault(digest(data[name].tolist()), []).append(name)
    registry = [
        {
            "feature": name,
            "family": schema[name],
            "distinct_development_values": int(distinct[name]),
            "minimum": float(data[name].min()),
            "maximum": float(data[name].max()),
            "nonzero_fraction": float((data[name] != 0).mean()),
            "availability": "current_and_past_legal_observations"
            if name.startswith(("history.", "market_history.", "cash_history."))
            else "current_legal_observation",
            "status": "coverage_gap_constant" if name in constants else "provisional_not_selected",
        }
        for name in columns
    ]
    pd.DataFrame(registry).to_csv(root / "reports/supply_registry.csv", index=False)
    corr = data[nonconstant].corr(method="spearman").to_numpy()
    correlations = [
        {"first": nonconstant[i], "second": nonconstant[j], "spearman": float(corr[i, j])}
        for i, j in zip(*np.where(np.triu(np.abs(corr) >= 0.995, k=1)), strict=True)
    ]
    pd.DataFrame(correlations, columns=["first", "second", "spearman"]).to_csv(
        root / "reports/supply_correlations.csv", index=False
    )
    matrix_lineage = {
        "study_sha256": digest(common),
        "schema": schema,
        "metadata_sha256": digest(metadata),
        "matrix_sha256": digest(matrix),
    }
    matrix_path = root / "artifacts/supply_features" / (digest(matrix_lineage) + ".json.gz")
    save_checkpoint(
        matrix_path, matrix_lineage, {"columns": columns, "rows": matrix, "metadata": metadata}
    )
    groups = (
        frame.groupby(["opponent", "arm"])
        .mean(numeric_only=True)
        .drop(columns=["seed", "seat"])
        .reset_index()
    )

    def timing(values):
        return {
            "median": float(np.median(values)),
            "p95": float(np.quantile(values, 0.95)),
            "max": max(values),
        }

    report = {
        "experiment": protocol["experiment"],
        "lineage": common,
        "protocol_sha256": digest(protocol),
        "games": len(rows),
        "seed_clusters": 4,
        "groups": groups.to_dict("records"),
        "effects": effects.to_dict("records"),
        "artifact_manifest": manifests,
        "execution_seconds": total_seconds,
        "policy_latency_ms": timing(latency),
        "sampled_feature_bank_latency_ms": timing(extraction),
        "screening": {
            "generated_features": len(columns),
            "screened_features": len(columns),
            "provisional_features": len(columns),
            "retained_for_final_model": 0,
            "rejected_for_final_model": 0,
            "sampled_development_observations": len(matrix),
            "families": dict(Counter(schema.values())),
            "constant_features": constants,
            "exact_duplicate_groups": [v for v in duplicates.values() if len(v) > 1],
            "high_spearman_pairs": len(correlations),
            "matrix_artifact": {
                "path": matrix_path.relative_to(root).as_posix(),
                "sha256": file_digest(matrix_path),
            },
            "scope": "Descriptive availability, variation, redundancy; not predictive selection",
        },
        "validation_or_holdout_used": False,
        "feature_completion_gate": "closed",
        "limitations": [
            "Four seed clusters: bootstrap intervals are descriptive, not confirmatory",
            "Two related frozen crop opponents are not a representative competition population",
            "Stock upper bounds are stress inputs, not calibrated probabilities or forecasts",
            "Same initial seed does not fix future shops after policy-induced RNG divergence",
            "Fixed holding and delivery logic; no final policy promotion or hyperparameter search",
            "Animals, fertilizer, land, broader routing and opponent diversity remain open",
        ],
    }
    write_json(root / "reports/supply_research.json", report)
    return report
