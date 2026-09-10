"""Preregistered 2x2 market/logistics study on six fresh development seeds."""

import copy
import time
from collections import Counter
from itertools import combinations, product
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
from kaggriculture_research.experiment import semantic_hash
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.market_features import market_features
from kaggriculture_research.market_policy import ARMS, FACTORS, MarketPolicy
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_research.relationship_policy import RelationshipPolicy


def run_game(seed: int, seat: int, arm: str, stride: int = 4) -> dict:
    candidate, opponent = MarketPolicy(arm), RelationshipPolicy("101")
    history = CausalHistory()
    records, latencies, feature_times, samples = [], [], [], []
    schema, columns, count = {}, [], Counter()
    minimum_cash = 3000

    def instrument(actor, is_candidate):
        def call(observation, configuration):
            nonlocal schema, columns, minimum_cash
            if configuration.get("seed") is not None:
                raise ValueError("Seed leaked into policy configuration")
            obs = {k: copy.deepcopy(observation[k]) for k in PUBLIC_FIELDS}
            before = copy.deepcopy(obs)
            start = time.perf_counter()
            action = actor(obs)
            elapsed = (time.perf_counter() - start) * 1000
            if obs != before:
                raise ValueError("Policy mutated its legal observation")
            record = {"player": obs["player"], "observation": before, "action": action}
            if is_candidate:
                latencies.append(elapsed)
                record["diagnostics"] = copy.deepcopy(actor.last_diagnostics)
                count.update(
                    {
                        f"interventions_{k}": v
                        for k, v in actor.last_diagnostics["interventions"].items()
                    }
                )
                start = time.perf_counter()
                past = history.observe(obs)  # Observe EVERY turn, even when the matrix is sampled.
                if obs["step"] % stride == 0 or obs["step"] == 718:
                    vectors = [
                        observe_features(obs),
                        relationship_features(obs),
                        past,
                        market_features(obs),
                    ]
                    values = {k: v for f in vectors for k, v in f.values.items()}
                    families = {k: v for f in vectors for k, v in f.families.items()}
                    if len(values) != sum(len(f.values) for f in vectors):
                        raise ValueError("Feature namespaces overlap")
                    if schema and schema != families:
                        raise ValueError("Feature schema drift")
                    schema = families
                    columns = list(values)
                    samples.append({"step": obs["step"], "values": list(values.values())})
                    feature_times.append((time.perf_counter() - start) * 1000)
                farm, private = copy.deepcopy(obs["farms"][seat]), copy.deepcopy(obs["private"])
                minimum_cash = min(minimum_cash, farm["money"])
                for i, unit_action in enumerate([action["farmer"], *action["hands"]]):
                    amount, shed = (
                        sum(private["inventories"][i].values()),
                        sum(private["shed"].values()),
                    )
                    shadow = (copy.deepcopy(farm), copy.deepcopy(private))
                    game._apply_unit_action(farm, private, i, unit_action, 10, obs["day"], 24, 100)
                    if unit_action[0] != "PASS" and shadow == (farm, private):
                        count["ineffective_farm_actions"] += 1
                    after = sum(private["inventories"][i].values())
                    if unit_action[0] == "HARVEST":
                        count["harvested_units"] += after - amount
                    elif unit_action[0] == "DROP":
                        count["discarded_units"] += (
                            amount - after - (sum(private["shed"].values()) - shed)
                        )
                    count["action_" + unit_action[0]] += 1
                for order in action["market"]:
                    if order[0] == "SELL":
                        _, item, quantity = order
                        if quantity > private["shed"].get(item, 0):
                            raise ValueError("Sale exceeds observable inventory")
                        private["shed"][item] -= quantity
                        count["sold_units"] += quantity
                    elif order[0] not in ("BUY_SEED", "HIRE"):
                        raise ValueError("This conservation contract is crop-only")
                if obs["hour"] == 23:
                    count["discarded_units"] += max(
                        0,
                        sum(private["shed"].values())
                        + sum(sum(inv.values()) for inv in private["inventories"])
                        - 100,
                    )
                if obs["step"] == 718:
                    count["terminal_standing_plants"] = sum(
                        isinstance(t, dict) and t.get("kind") == "PLANT"
                        for row in farm["tiles"]
                        for t in row
                    )
            records.append(record)
            return action

        return call

    env = make_environment(seed, {"episodeSteps": 720})
    actors = [instrument(candidate, True), instrument(opponent, False)]
    env.run(actors if seat == 0 else list(reversed(actors)))
    statuses = [s.status for s in env.state]
    if statuses != ["DONE", "DONE"] or len(env.steps) != 720 or len(latencies) != 719:
        raise ValueError("Incomplete official episode")
    rewards = [s.reward for s in env.state]
    private = env.state[seat].observation["private"]  # Evaluator only, never feature input.
    unsold = sum(
        n
        for inv in [private["shed"], *private["inventories"]]
        for c, n in inv.items()
        if c in game.PRODUCTS
    )
    if count["harvested_units"] != count["sold_units"] + count["discarded_units"] + unsold:
        raise ValueError("Exact crop-product conservation failed")
    summary = {
        "seed": seed,
        "seat": seat,
        "arm": arm,
        "match_score": float(rewards[seat] > rewards[1 - seat])
        + 0.5 * (rewards[seat] == rewards[1 - seat]),
        "coins": rewards[seat],
        "coin_margin": rewards[seat] - rewards[1 - seat],
        "unsold_product_units": unsold,
        "minimum_observed_cash": minimum_cash,
        **{f: int(b) for f, b in zip(FACTORS, arm, strict=True)},
        **{
            k: count[k]
            for k in (
                "harvested_units",
                "sold_units",
                "discarded_units",
                "ineffective_farm_actions",
                "terminal_standing_plants",
            )
        },
        **{f"interventions_{k}": count[f"interventions_{k}"] for k in FACTORS},
        **{
            f"action_{k}": count[f"action_{k}"]
            for k in ("HARVEST", "WATER", "DROP", "PLACE", "PASS")
        },
    }
    payload = {
        "summary": summary,
        "records": records,
        "states": 720,
        "statuses": statuses,
        "latency_ms": latencies,
        "feature_schema": schema,
        "feature_columns": columns,
        "feature_samples": samples,
        "feature_extraction_ms": feature_times,
    }
    # Runtime is deliberately excluded from the semantic identity, just as in study 1.
    payload["semantic_sha256"] = episode_hash(payload)
    return payload


def episode_hash(payload: dict) -> str:
    return semantic_hash({k: v for k, v in payload.items() if k != "feature_extraction_ms"})


def factorial_summary(frame: pd.DataFrame, resamples: int, bootstrap_seed: int) -> pd.DataFrame:
    """Main effects, averaged pairwise difference-in-differences contrast.

    Unlike ±1 regression coefficients, these are ON-minus-OFF effects in outcome
    units. Both seats and all nuisance-factor levels remain within each seed.
    Bootstrap intervals are descriptive; six clusters cannot establish generality.
    """
    rng, rows = np.random.default_rng(bootstrap_seed), []
    if frame.duplicated(["seed", "seat", "arm"]).any():
        raise ValueError("Duplicated factorial episode")
    for _, group in frame.groupby(["seed", "seat"]):
        if set(group.arm) != set(ARMS):
            raise ValueError("Incomplete factorial block")
    for size in (1, 2):
        for factors in combinations(FACTORS, size):
            signs = np.prod([2 * frame[f].to_numpy() - 1 for f in factors], axis=0)
            for metric in (
                "match_score",
                "coins",
                "coin_margin",
                "discarded_units",
                "minimum_observed_cash",
            ):
                clusters = (frame[metric] * signs).groupby(frame.seed).mean() * (2**size)
                draws = rng.choice(
                    clusters.to_numpy(), size=(resamples, len(clusters)), replace=True
                ).mean(axis=1)
                rows.append(
                    {
                        "contrast": ":".join(factors),
                        "order": size,
                        "metric": metric,
                        "effect": float(clusters.mean()),
                        "bootstrap_low": float(np.quantile(draws, 0.025)),
                        "bootstrap_high": float(np.quantile(draws, 0.975)),
                        "seed_clusters": len(clusters),
                        "seed_differences": clusters.to_json(),
                    }
                )
    return pd.DataFrame(rows)


def screen_features(root: Path, matrix: pd.DataFrame, metadata: pd.DataFrame, schema: dict) -> dict:
    if not np.isfinite(matrix.to_numpy()).all():
        raise ValueError("Non-finite feature matrix")
    distinct = matrix.nunique()
    constants = distinct[distinct <= 1].index.tolist()
    groups = {}
    for name in matrix:
        if name not in constants:
            groups.setdefault(digest(matrix[name].tolist()), []).append(name)
    duplicates = [names for names in groups.values() if len(names) > 1]
    correlated = []
    nonconstant = [n for n in matrix if n not in constants]
    corr = matrix[nonconstant].corr(method="spearman").to_numpy()
    for i, j in zip(*np.where(np.triu(np.abs(corr) >= 0.995, k=1)), strict=True):
        correlated.append(
            {"first": nonconstant[i], "second": nonconstant[j], "spearman": float(corr[i, j])}
        )
    pd.DataFrame(correlated, columns=["first", "second", "spearman"]).to_csv(
        root / "reports/market_correlations.csv", index=False
    )
    registry = []
    for name in matrix:
        registry.append(
            {
                "feature": name,
                "family": schema[name],
                "distinct_development_values": int(distinct[name]),
                "minimum": float(matrix[name].min()),
                "maximum": float(matrix[name].max()),
                "nonzero_fraction": float((matrix[name] != 0).mean()),
                "availability": "current_and_past_legal_observations"
                if name.startswith("history.")
                else "current_legal_observation",
                "status": "coverage_gap_constant"
                if name in constants
                else "provisional_not_selected",
            }
        )
    pd.DataFrame(registry).to_csv(root / "reports/market_registry.csv", index=False)
    # Rows are retained privately with episode keys; never use random turn-level folds.
    lineage = {
        "schema": schema,
        "matrix_sha256": digest(matrix.to_numpy().tolist()),
        "metadata_sha256": digest(metadata.to_dict("records")),
    }
    path = root / "artifacts/market_features" / (digest(lineage) + ".json.gz")
    save_checkpoint(
        path,
        lineage,
        {
            "columns": list(matrix),
            "rows": matrix.to_numpy().tolist(),
            "metadata": metadata.to_dict("records"),
        },
    )
    return {
        "generated_features": len(matrix.columns),
        "screened_features": len(matrix.columns),
        "retained_for_final_model": 0,
        "rejected_for_final_model": 0,
        "provisional_features": len(matrix.columns),
        "sampled_development_observations": len(matrix),
        "families": dict(Counter(schema.values())),
        "constant_features": constants,
        "exact_duplicate_groups": duplicates,
        "high_spearman_pairs": len(correlated),
        "matrix_artifact": {"path": path.relative_to(root).as_posix(), "sha256": file_digest(path)},
        "screening_scope": (
            "availability, finite/schema, empirical variation, exact duplication and "
            "correlation; not predictive selection"
        ),
        "warning": (
            "Constants/duplicates are coverage flags, not rejection evidence; "
            "animal treatments lack rollout support."
        ),
    }


def run_experiment(
    root: Path, protocol: dict, foundation: dict, progress: Progress, checkpoint_ready=None
) -> dict:
    validate_protocol(foundation)
    if (
        set(protocol["development_seeds"])
        & set(
            foundation["development_seeds"]
            + foundation["validation_seeds"]
            + foundation["holdout_seeds"]
        )
        or protocol["configuration"] != foundation["configuration"]
    ):
        raise ValueError("Development boundary or official configuration changed")
    if protocol["arms"] != list(ARMS) or protocol["factors"] != list(FACTORS):
        raise ValueError("Registered factorial design changed")
    source = Path(__file__).parent
    for name, expected in protocol["frozen_sources"].items():
        if file_digest(source / name) != expected:
            raise ValueError(f"Frozen reference changed: {name}")
    if (
        protocol["maximum_hold_actions"] != 4
        or protocol["rival_scenario_weight"] != 0.5
        or protocol["baseline_relationship_arm"] != "001"
        or protocol["opponent_relationship_arm"] != "101"
        or protocol["feature_horizons"] != [4, 12, 24]
        or protocol["seats"] != [0, 1]
        or len(set(protocol["development_seeds"])) != 6
        or protocol["max_games"] != 48
    ):
        raise ValueError("Registered intervention or fresh-seed design changed")
    jobs = list(product(protocol["development_seeds"], protocol["seats"], protocol["arms"]))
    if len(jobs) != protocol["max_games"]:
        raise ValueError("Registered game budget mismatch")
    common = {
        "engine": engine_manifest(),
        "protocol": protocol,
        "code": {p.name: file_digest(p) for p in sorted(source.glob("*.py"))},
    }
    start = time.monotonic()
    rows, matrices, metadata, manifests = [], [], [], []
    latency, feature_latency, schema, columns, reused = [], [], {}, [], 0
    for seed, seat, arm in jobs:
        if time.monotonic() - start >= protocol["max_seconds"]:
            raise TimeoutError("Bounded experiment expired; completed episodes are reusable")
        lineage = {**common, "seed": seed, "seat": seat, "arm": arm}
        path = root / "artifacts/market_episodes" / (digest(lineage) + ".json.gz")
        with progress.stage(f"markets_{seed}_seat{seat}_arm{arm}"):
            payload = load_checkpoint(path, lineage)
            if payload is None:
                payload = run_game(seed, seat, arm, protocol["feature_sample_stride"])
                save_checkpoint(path, lineage, payload)
            else:
                reused += 1
            if episode_hash(payload) != payload["semantic_sha256"]:
                raise ValueError("Semantic identity differs from checkpoint")
            if checkpoint_ready:
                checkpoint_ready(path)
            if schema and schema != payload["feature_schema"]:
                raise ValueError("Feature schema drift across games")
            if columns and columns != payload["feature_columns"]:
                raise ValueError("Feature column order drift across checkpoints")
            schema = payload["feature_schema"]
            columns = payload["feature_columns"]
            rows.append(payload["summary"])
            latency.extend(payload["latency_ms"])
            feature_latency.extend(payload["feature_extraction_ms"])
            for sample in payload["feature_samples"]:
                matrices.append(sample["values"])
                metadata.append({"seed": seed, "seat": seat, "arm": arm, "step": sample["step"]})
            manifests.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": file_digest(path),
                    "semantic_sha256": payload["semantic_sha256"],
                }
            )
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "reports/market_games.csv", index=False)
    effects = factorial_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    effects.to_csv(root / "reports/market_effects.csv", index=False)
    with progress.stage("causal_feature_screening"):
        screening = screen_features(
            root, pd.DataFrame(matrices, columns=columns), pd.DataFrame(metadata), schema
        )
    groups = (
        frame.groupby("arm").mean(numeric_only=True).drop(columns=["seed", "seat"]).reset_index()
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
        "reused_games": reused,
        "seed_clusters": len(protocol["development_seeds"]),
        "groups": groups.to_dict("records"),
        "effects": effects.to_dict("records"),
        "screening": screening,
        "policy_latency_ms": timing(latency),
        "sampled_feature_bank_latency_ms": timing(feature_latency),
        "conservation_verified_games": len(rows),
        "artifact_manifest": manifests,
        "validation_or_holdout_used": False,
        "feature_completion_gate": "closed",
        "limitations": [
            "Six fresh development seeds; no confirmatory inference or multiple-testing claim",
            "One frozen capacity-plus-maturity opponent; no broad opponent population yet",
            "Two fixed interventions; descriptive feature coverage is not predictive selection",
            "Same initial seed does not fix future shops after policy-induced RNG divergence",
            "Rival visible supply is a stress envelope, not a forecast of hidden stocks/actions",
            "Delivery uses a work-value proxy, not globally optimized worker routes",
            "Market timing uses fixed scenario weights, not calibrated probabilities",
            "Known-shop demand is conditional on no unobserved future shop additions",
        ],
    }
    write_json(root / "reports/market_research.json", report)
    return report
