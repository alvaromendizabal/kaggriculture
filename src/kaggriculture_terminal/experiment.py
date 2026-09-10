"""Preregistered sequential resource-loop ablations with episode-atomic recovery."""

import copy
import json
import time
from collections import Counter
from collections.abc import Callable
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_livestock.audit import accounting
from kaggriculture_livestock.features import livestock_features
from kaggriculture_livestock.policy import LivestockPolicy
from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.crop_policy import CropPolicy
from kaggriculture_research.environment import engine_manifest, make_environment, validate_protocol
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.market_features import market_features
from kaggriculture_research.market_history import MarketHistory
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_terminal.policy import ARMS, TerminalPolicy
from kaggriculture_terminal.routing import ITEMS, terminal_features

KEYS = ("seed", "seat", "opponent", "arm")
OPPONENTS = ("livestock_fertilizer", "melon_specialist")
CONTRASTS = (("feed", "baseline"), ("joint", "feed"), ("joint", "baseline"))
METRICS = (
    "match_score",
    "coins",
    "coin_margin",
    "fed_units",
    "commands_CARE",
    "applied_units",
    "escaped_animals",
    "discarded_units",
    "terminal_feed",
    "terminal_noops",
    "residual_product_units",
    "uncollected_manure_slots",
    "overflow_production_units",
)


def feature_bank(obs: dict, past, market_past) -> tuple[dict, dict]:
    vectors = [
        observe_features(obs),
        relationship_features(obs),
        past,
        market_features(obs),
        market_past,
        livestock_features(obs),
        terminal_features(obs),
    ]
    values = {k: v for f in vectors for k, v in f.values.items()}
    schema = {k: v for f in vectors for k, v in f.families.items()}
    if len(values) != 1579 or len(values) != sum(len(f.values) for f in vectors):
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
    candidate = TerminalPolicy(arm)
    rival = (
        CropPolicy("full", fixed_crop="MELON")
        if opponent == "melon_specialist"
        else LivestockPolicy("fertilizer")
    )
    causal, history = CausalHistory(), MarketHistory()
    records, latencies, feature_times, samples = [], [], [], []
    columns, schema, count, maxima = [], {}, Counter(), Counter()
    minimum_cash, started = 3000, time.monotonic()

    def instrument(actor, is_candidate):
        def call(observation, configuration):
            nonlocal candidate, history, schema, columns, minimum_cash
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
                for species, n in candidate.last_diagnostics["animal_counts"].items():
                    maxima[species] = max(maxima[species], n)
                minimum_cash = min(minimum_cash, obs["farms"][seat]["money"])
                past, market_past = causal.observe(obs), history.observe(obs)
                if obs["step"] % stride == 0 or obs["step"] == 718:
                    tick = time.perf_counter()
                    values, families = feature_bank(obs, past, market_past)
                    if schema and (schema != families or columns != list(values)):
                        raise ValueError("Feature schema drift")
                    schema, columns = families, list(values)
                    samples.append({"step": obs["step"], "values": list(values.values())})
                    feature_times.append((time.perf_counter() - tick) * 1000)
                history.record_action(action)
                if obs["step"] % 24 == 0 or obs["step"] == 718:
                    candidate = TerminalPolicy.from_state_dict(candidate.state_dict())
                    history = MarketHistory.from_json(history.to_json())
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
    payload = {
        "records": records,
        "states": 720,
        "statuses": statuses,
        "rewards": rewards,
        "evaluator_terminal_observations": [
            {
                **{k: copy.deepcopy(env.state[0].observation[k]) for k in PUBLIC_FIELDS},
                "player": player,
                "private": copy.deepcopy(s.observation["private"]),
            }
            for player, s in enumerate(env.state)
        ],
        "feature_columns": columns,
        "feature_schema": schema,
        "feature_samples": samples,
        "latency_ms": latencies,
        "feature_extraction_ms": feature_times,
    }
    audit = accounting(payload)
    margin = rewards[seat] - rewards[1 - seat]
    counts = Counter(audit["players"][seat])
    for name in METRICS[3:]:
        counts.setdefault(name, 0)
    payload["summary"] = {
        "seed": seed,
        "seat": seat,
        "opponent": opponent,
        "arm": arm,
        "match_score": float(margin > 0) + 0.5 * (margin == 0),
        "coins": rewards[seat],
        "coin_margin": margin,
        "minimum_observed_cash": minimum_cash,
        "state_roundtrips": count["state_roundtrips"],
        **dict(counts),
        **{"maximum_" + k: maxima[k] for k in ("GOOSE", "COW", "SHEEP")},
    }
    terminal_records = [r for r in records if r["player"] == seat and r["observation"]["day"] == 29]
    terminal_commands = Counter(
        a[0] for r in terminal_records for a in [r["action"]["farmer"], *r["action"]["hands"]]
    )
    for op in ("FEED", "CARE", "WATER", "DROP", "PASS"):
        payload["summary"]["terminal_" + op.lower()] = terminal_commands[op]
    payload["summary"]["terminal_noops"] = sum(
        r["diagnostics"]["ineffective_farm_actions"] for r in terminal_records
    )
    final = payload["evaluator_terminal_observations"][seat]
    payload["summary"]["residual_product_units"] = sum(
        n
        for inv in [final["private"]["shed"], *final["private"]["inventories"]]
        for item, n in inv.items()
        if item in ITEMS
    )
    payload["preterminal_sha256"] = digest([r for r in records if r["observation"]["step"] < 696])
    payload["accounting"] = audit
    payload["execution_seconds"] = time.monotonic() - started
    payload["semantic_sha256"] = episode_hash(payload)
    validate_episode(payload, {k: payload["summary"][k] for k in KEYS})
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
        len(payload["feature_columns"]) != 1579
        or len(set(payload["feature_columns"])) != 1579
        or set(payload["feature_columns"]) != set(payload["feature_schema"])
    ):
        raise ValueError("Checkpoint feature schema differs")
    for sample in payload["feature_samples"]:
        if len(sample["values"]) != 1579 or not np.isfinite(sample["values"]).all():
            raise ValueError("Invalid checkpoint feature vector")
    row, rewards = payload["summary"], payload["rewards"]
    margin = rewards[row["seat"]] - rewards[1 - row["seat"]]
    if (
        row["coins"] != rewards[row["seat"]]
        or row["coin_margin"] != margin
        or row["match_score"] != float(margin > 0) + 0.5 * (margin == 0)
    ):
        raise ValueError("Checkpoint outcome inconsistent")
    if payload["accounting"]["transitions"] != 1438:
        raise ValueError("Transition accounting incomplete")


def common_lineage(root: Path, protocol: dict) -> dict:
    foundation = json.loads((root / "configs/research.json").read_text())
    validate_protocol(foundation)
    forbidden = set(
        foundation["development_seeds"]
        + foundation["validation_seeds"]
        + foundation["holdout_seeds"]
        + [61, 71]
    )
    for name in ("market", "supply", "livestock"):
        forbidden.update(
            json.loads((root / f"configs/{name}_research.json").read_text())["development_seeds"]
        )
    if (
        protocol["development_seeds"] != [1501, 1502, 1503, 1504]
        or set(protocol["development_seeds"]) & forbidden
        or protocol["arms"] != list(ARMS)
        or protocol["opponents"] != list(OPPONENTS)
        or protocol["contrasts"] != [list(c) for c in CONTRASTS]
        or protocol["max_games"] != 48
        or protocol["seats"] != [0, 1]
        or protocol["configuration"] != {"episodeSteps": 720}
    ):
        raise ValueError("Registered terminal design or seed separation changed")
    frozen = json.loads((root / "reports/livestock_registration.json").read_text())["identity"][
        "lineage"
    ]["code"]
    for path, sha in frozen.items():
        if file_digest(root / path) != sha:
            raise ValueError("Frozen prior source changed: " + path)
    files = [
        *sorted((root / "src/kaggriculture_research").glob("*.py")),
        *sorted((root / "src/kaggriculture_livestock").glob("*.py")),
        *sorted((root / "src/kaggriculture_terminal").glob("*.py")),
        root / "docs/terminal_protocol.md",
    ]
    return {
        "engine": engine_manifest(),
        "protocol": protocol,
        "code": {p.relative_to(root).as_posix(): file_digest(p) for p in files},
    }


def job_plan(root: Path, protocol: dict) -> tuple[dict, list[dict]]:
    common, jobs = common_lineage(root, protocol), []
    for values in product(
        *(protocol[k] for k in ("development_seeds", "seats", "opponents", "arms"))
    ):
        key = dict(zip(KEYS, values, strict=True))
        lineage = {**common, **key}
        jobs.append(
            {
                "key": key,
                "lineage": lineage,
                "path": "artifacts/terminal_episodes/" + digest(lineage) + ".json.gz",
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
            with progress.stage("terminal_" + "_".join(map(str, job["key"].values()))):
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
                "preterminal_sha256": payload["preterminal_sha256"],
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
        "feature_completion_gate": "open_research",
    }
    write_json(root / "reports/terminal_progress.json", status)
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
                "preterminal_sha256": payload["preterminal_sha256"],
            }
        )
    prefixes = (
        pd.DataFrame(manifests)
        .groupby(["seed", "seat", "opponent"])["preterminal_sha256"]
        .nunique()
    )
    if len(prefixes) != 16 or not (prefixes == 1).all():
        raise ValueError("Preterminal paired policies diverged before intervention")
    frame = pd.DataFrame(rows)
    for col in frame.columns:
        if col.startswith("commands_"):
            frame[col] = frame[col].fillna(0)
    frame.to_csv(root / "reports/terminal_games.csv", index=False)
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    effects.to_csv(root / "reports/terminal_effects.csv", index=False)
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
    pd.DataFrame(registry).to_csv(root / "reports/terminal_registry.csv", index=False)
    corr = data[nonconstant].corr(method="spearman").to_numpy()
    correlations = [
        {"first": nonconstant[i], "second": nonconstant[j], "spearman": float(corr[i, j])}
        for i, j in zip(*np.where(np.triu(np.abs(corr) >= 0.995, k=1)), strict=True)
    ]
    pd.DataFrame(correlations, columns=["first", "second", "spearman"]).to_csv(
        root / "reports/terminal_correlations.csv", index=False
    )
    matrix_lineage = {
        "study_sha256": digest(common),
        "schema": schema,
        "metadata_sha256": digest(metadata),
        "matrix_sha256": digest(matrix),
    }
    matrix_path = root / "artifacts/terminal_features" / (digest(matrix_lineage) + ".json.gz")
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
        "identical_preterminal_blocks": len(prefixes),
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
        "feature_completion_gate": "open_research",
        "limitations": [
            "Four seed clusters: bootstrap intervals are descriptive, not confirmatory",
            "Two fixed opponents do not represent the competition population",
            "Fertilizer rollouts assume fixed tile continuation and current quote curves",
            "The 42 prior cash-bound features are excluded because this policy buys products",
            "Same initial seed does not fix future shops after policy-induced RNG divergence",
            "Sequential ablations are conditional effects, not factorial main effects",
            "Bounded final-day routes are not globally optimal season-long assignments",
            "Herd layouts, capital stress and independent opponent populations remain open",
        ],
    }
    write_json(root / "reports/terminal_research.json", report)
    return report
