"""Preregistered staffing-controlled routing pilot with episode-atomic recovery.

This module isolates terminal farm-unit routing from the shared hiring/market rule.
It never accesses validation/holdout seeds and never performs network I/O during an
episode. Durable uploads are handled only after a complete validated checkpoint.
"""

from __future__ import annotations

import copy
import json
import time
from collections import Counter
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_livestock.audit import accounting
from kaggriculture_livestock.policy import LivestockPolicy
from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, save_checkpoint, write_json
from kaggriculture_research.environment import engine_manifest, make_environment, validate_protocol
from kaggriculture_research.features import PUBLIC_FIELDS
from kaggriculture_staffing.features import FEATURE_COUNT, staffing_features
from kaggriculture_staffing.policy import ARMS, StaffingPolicy
from kaggriculture_terminal.routing import ITEMS

KEYS = ("seed", "seat", "opponent", "arm")
OPPONENTS = ("livestock_fertilizer",)
CONTRASTS = (("coordinated", "sequential"),)
METRICS = (
    "match_score",
    "coins",
    "coin_margin",
    "terminal_residual_product_units",
    "terminal_active_worker_mean",
    "terminal_routed_worker_mean",
    "terminal_coordination_gap_mean",
    "terminal_multiworker_callbacks",
    "terminal_route_activations",
    "terminal_noops",
)


def episode_hash(payload: dict) -> str:
    """Semantic checkpoint identity excluding nondeterministic timing measurements."""
    return digest(
        {
            key: value
            for key, value in payload.items()
            if key not in ("latency_ms", "execution_seconds", "semantic_sha256")
        }
    )


def run_activation_preflight(seed: int) -> dict:
    """Run one non-scored development trajectory and prove final-day multiworker activation."""
    candidate = StaffingPolicy("sequential")
    rival = LivestockPolicy("fertilizer")
    active, latencies = [], []

    def instrument(actor, candidate_side: bool):
        def call(observation, configuration):
            if configuration.get("seed") is not None:
                raise ValueError("Seed leaked into policy configuration")
            obs = {key: copy.deepcopy(observation[key]) for key in PUBLIC_FIELDS}
            tick = time.perf_counter()
            action = candidate(obs) if candidate_side else actor(obs)
            if candidate_side:
                latencies.append((time.perf_counter() - tick) * 1000)
                if obs["day"] == 29:
                    active.append(candidate.last_diagnostics["active_workers"])
            return action

        return call

    env = make_environment(seed, {"episodeSteps": 720})
    env.run([instrument(candidate, True), instrument(rival, False)])
    statuses = [state.status for state in env.state]
    if statuses != ["DONE", "DONE"] or len(env.steps) != 720:
        raise ValueError("Activation preflight did not complete the official horizon")
    if not active or max(active) < 2:
        raise ValueError("Staffing intervention never reaches two active workers")
    return {
        "seed": seed,
        "terminal_callbacks": len(active),
        "multiworker_callbacks": sum(value >= 2 for value in active),
        "maximum_active_workers": max(active),
        "policy_latency_ms": {
            "p95": float(np.quantile(latencies, 0.95)),
            "max": float(max(latencies)),
        },
        "outcome_recorded": False,
    }


def run_game(seed: int, seat: int, opponent: str, arm: str) -> dict:
    """Execute one frozen pilot episode and return a fully self-validating checkpoint."""
    if opponent not in OPPONENTS or seat not in (0, 1) or arm not in ARMS:
        raise ValueError("Unregistered staffing episode design")
    candidate = StaffingPolicy(arm)
    rival = LivestockPolicy("fertilizer")
    records, latencies, samples = [], [], []
    started = time.monotonic()

    def instrument(actor, candidate_side: bool):
        def call(observation, configuration):
            if configuration.get("seed") is not None:
                raise ValueError("Seed leaked into policy configuration")
            obs = {key: copy.deepcopy(observation[key]) for key in PUBLIC_FIELDS}
            before = copy.deepcopy(obs)
            tick = time.perf_counter()
            action = candidate(obs) if candidate_side else actor(obs)
            elapsed = (time.perf_counter() - tick) * 1000
            if obs != before:
                raise ValueError("Policy mutated its legal observation")
            record = {"player": obs["player"], "observation": before, "action": copy.deepcopy(action)}
            if candidate_side:
                latencies.append(elapsed)
                record["diagnostics"] = copy.deepcopy(candidate.last_diagnostics)
                if obs["day"] == 29:
                    vector = staffing_features(obs)
                    samples.append(
                        {
                            "step": obs["step"],
                            "values": dict(vector.values),
                            "families": dict(vector.families),
                        }
                    )
            records.append(record)
            return action

        return call

    env = make_environment(seed, {"episodeSteps": 720})
    actors = [instrument(candidate, True), instrument(rival, False)]
    env.run(actors if seat == 0 else list(reversed(actors)))
    statuses = [state.status for state in env.state]
    rewards = [state.reward for state in env.state]
    candidate_records = [row for row in records if row["player"] == seat]
    if statuses != ["DONE", "DONE"] or len(env.steps) != 720 or len(candidate_records) != 719:
        raise ValueError("Incomplete staffing pilot episode")
    if [row["observation"]["step"] for row in candidate_records] != list(range(719)):
        raise ValueError("Candidate callback sequence differs from the pinned local engine")
    terminal = [row for row in candidate_records if row["observation"]["day"] == 29]
    if len(samples) != len(terminal):
        raise ValueError("Final-day staffing features were not sampled for every callback")
    if any(len(sample["values"]) != FEATURE_COUNT for sample in samples):
        raise ValueError("Staffing feature schema drift")

    audit = accounting(
        {
            "records": records,
            "states": 720,
            "statuses": statuses,
            "rewards": rewards,
            "evaluator_terminal_observations": [
                {
                    **{key: copy.deepcopy(env.state[0].observation[key]) for key in PUBLIC_FIELDS},
                    "player": player,
                    "private": copy.deepcopy(state.observation["private"]),
                }
                for player, state in enumerate(env.state)
            ],
        }
    )
    final = env.state[seat].observation
    residual = sum(
        quantity
        for inventory in [final["private"]["shed"], *final["private"]["inventories"]]
        for item, quantity in inventory.items()
        if item in ITEMS
    )
    active_workers = [row["diagnostics"]["active_workers"] for row in terminal]
    routed_workers = [
        row["diagnostics"]["staffing_features"]["staffing.active_routed_workers"] for row in terminal
    ]
    coordination_gap = [
        row["diagnostics"]["staffing_features"]["staffing.optimistic_coordination_gap"]
        for row in terminal
    ]
    noops = sum(
        row["diagnostics"].get("route_diagnostics", {}).get("ineffective_farm_actions", 0)
        for row in terminal
    )
    route_activations = sum(value >= 2 for value in routed_workers) if arm == "coordinated" else 0
    margin = rewards[seat] - rewards[1 - seat]
    summary = {
        "seed": seed,
        "seat": seat,
        "opponent": opponent,
        "arm": arm,
        "match_score": float(margin > 0) + 0.5 * (margin == 0),
        "coins": rewards[seat],
        "coin_margin": margin,
        "terminal_residual_product_units": residual,
        "terminal_active_worker_mean": float(np.mean(active_workers)),
        "terminal_routed_worker_mean": float(np.mean(routed_workers)),
        "terminal_coordination_gap_mean": float(np.mean(coordination_gap)),
        "terminal_multiworker_callbacks": int(sum(value >= 2 for value in active_workers)),
        "terminal_route_activations": int(route_activations),
        "terminal_noops": int(noops),
        "policy_latency_p95_ms": float(np.quantile(latencies, 0.95)),
        "policy_latency_max_ms": float(max(latencies)),
    }
    payload = {
        "records": records,
        "states": 720,
        "statuses": statuses,
        "rewards": rewards,
        "summary": summary,
        "feature_samples": samples,
        "accounting": audit,
        "latency_ms": latencies,
        "preterminal_sha256": digest(
            [row for row in candidate_records if row["observation"]["day"] < 29]
        ),
        "execution_seconds": time.monotonic() - started,
    }
    payload["semantic_sha256"] = episode_hash(payload)
    validate_episode(payload, {key: summary[key] for key in KEYS})
    return payload


def validate_episode(payload: dict, key: dict) -> None:
    """Fail closed on stale, incomplete or semantically inconsistent checkpoints."""
    if {name: payload["summary"][name] for name in KEYS} != key:
        raise ValueError("Checkpoint job identity differs")
    if payload["semantic_sha256"] != episode_hash(payload):
        raise ValueError("Checkpoint semantic identity differs")
    if payload["states"] != 720 or payload["statuses"] != ["DONE", "DONE"]:
        raise ValueError("Checkpoint episode incomplete")
    if payload["accounting"]["transitions"] != 1438:
        raise ValueError("Transition accounting incomplete")
    if payload["summary"]["policy_latency_max_ms"] > 500:
        raise ValueError("Registered policy latency budget exceeded")
    for sample in payload["feature_samples"]:
        if len(sample["values"]) != FEATURE_COUNT or not np.isfinite(list(sample["values"].values())).all():
            raise ValueError("Invalid staffing feature vector")


def common_lineage(root: Path, protocol: dict) -> dict:
    """Freeze the pilot against prior research sources and every protected seed partition."""
    foundation = json.loads((root / "configs/research.json").read_text())
    validate_protocol(foundation)
    forbidden = set(
        foundation["development_seeds"]
        + foundation["validation_seeds"]
        + foundation["holdout_seeds"]
        + [protocol["preflight_seed"]]
    )
    for name in ("market", "supply", "livestock", "terminal"):
        forbidden.update(
            json.loads((root / f"configs/{name}_research.json").read_text())["development_seeds"]
        )
    if (
        protocol["development_seeds"] != [1601, 1602]
        or set(protocol["development_seeds"]) & forbidden
        or protocol["arms"] != list(ARMS)
        or protocol["opponents"] != list(OPPONENTS)
        or protocol["contrasts"] != [list(value) for value in CONTRASTS]
        or protocol["max_games"] != 8
        or protocol["max_new_games_per_batch"] != 1
        or protocol["validation_allowed"]
        or protocol["holdout_allowed"]
        or protocol["scale_up_automatic"]
    ):
        raise ValueError("Registered staffing design or seed separation changed")
    files = [
        root / "configs/staffing_research.json",
        root / "docs/staffing_protocol.md",
        *sorted((root / "src/kaggriculture_staffing").glob("*.py")),
        root / "src/kaggriculture_terminal/routing.py",
        root / "src/kaggriculture_terminal/feed_policy.py",
        root / "src/kaggriculture_livestock/policy.py",
    ]
    return {
        "engine": engine_manifest(),
        "protocol": protocol,
        "code": {path.relative_to(root).as_posix(): file_digest(path) for path in files},
    }


def job_plan(root: Path, protocol: dict) -> tuple[dict, list[dict]]:
    common, jobs = common_lineage(root, protocol), []
    for values in product(
        *(protocol[name] for name in ("development_seeds", "seats", "opponents", "arms"))
    ):
        key = dict(zip(KEYS, values, strict=True))
        lineage = {**common, **key}
        jobs.append(
            {
                "key": key,
                "lineage": lineage,
                "path": "artifacts/staffing_episodes/" + digest(lineage) + ".json.gz",
            }
        )
    if len(jobs) != protocol["max_games"]:
        raise ValueError("Registered staffing job count differs")
    return common, jobs


def run_batch(root: Path, protocol: dict) -> dict:
    """Run at most one missing game; never overwrite a mismatched checkpoint."""
    common, jobs = job_plan(root, protocol)
    new = reused = 0
    manifests = []
    started = time.monotonic()
    for job in jobs:
        path = root / job["path"]
        payload = load_checkpoint(path, job["lineage"])
        if path.exists() and payload is None:
            raise ValueError("Existing checkpoint has different lineage; do not overwrite")
        if payload is None:
            if new >= 1 or time.monotonic() - started >= protocol["max_seconds_per_batch"]:
                break
            payload = run_game(**job["key"])
            save_checkpoint(path, job["lineage"], payload)
            new += 1
        else:
            reused += 1
        validate_episode(payload, job["key"])
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
    write_json(root / "reports/staffing_progress.json", status)
    return status


def paired_summary(frame: pd.DataFrame, resamples: int, bootstrap_seed: int) -> pd.DataFrame:
    """Seed-cluster descriptive contrasts for the tiny preregistered mechanism pilot."""
    if frame.duplicated(list(KEYS)).any():
        raise ValueError("Duplicated paired episode")
    for _, group in frame.groupby(["seed", "seat", "opponent"]):
        if set(group.arm) != set(ARMS):
            raise ValueError("Incomplete paired block")
    indexed = frame.set_index(["seed", "seat", "opponent", "arm"])
    rng, rows = np.random.default_rng(bootstrap_seed), []
    for treatment, control in CONTRASTS:
        for metric in METRICS:
            delta = indexed[metric].xs(treatment, level="arm") - indexed[metric].xs(
                control, level="arm"
            )
            clusters = delta.groupby(level="seed").mean()
            draws = rng.choice(clusters.to_numpy(), size=(resamples, len(clusters)), replace=True).mean(axis=1)
            rows.append(
                {
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
    """Summarize only after all eight registered checkpoints validate and pair cleanly."""
    common, jobs = job_plan(root, protocol)
    rows, manifests, feature_rows, latency = [], [], [], []
    families: dict[str, str] = {}
    total_seconds = 0.0
    for job in jobs:
        path = root / job["path"]
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            raise ValueError("Cannot summarize an incomplete staffing pilot")
        validate_episode(payload, job["key"])
        rows.append(payload["summary"])
        latency.extend(payload["latency_ms"])
        total_seconds += payload["execution_seconds"]
        for sample in payload["feature_samples"]:
            feature_rows.append({**job["key"], "step": sample["step"], **sample["values"]})
            if not families:
                families = sample["families"]
            elif families != sample["families"]:
                raise ValueError("Between-episode staffing feature schema drift")
        manifests.append(
            {
                **job["key"],
                "path": job["path"],
                "sha256": file_digest(path),
                "semantic_sha256": payload["semantic_sha256"],
                "preterminal_sha256": payload["preterminal_sha256"],
            }
        )
    prefix_counts = (
        pd.DataFrame(manifests).groupby(["seed", "seat", "opponent"])["preterminal_sha256"].nunique()
    )
    if len(prefix_counts) != 4 or not (prefix_counts == 1).all():
        raise ValueError("Paired policies diverged before the day-29 intervention")
    frame = pd.DataFrame(rows)
    if frame["terminal_multiworker_callbacks"].max() < protocol["minimum_multiworker_callbacks"]:
        raise ValueError("Pilot never activated multiple workers")
    coordinated = frame[frame.arm == "coordinated"]
    if coordinated["terminal_route_activations"].sum() == 0:
        raise ValueError("Coordinated route mechanism never activated")
    if coordinated["terminal_noops"].sum() != 0:
        raise ValueError("Coordinated routing produced ineffective farm actions")
    frame.to_csv(root / "reports/staffing_games.csv", index=False)
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    effects.to_csv(root / "reports/staffing_effects.csv", index=False)
    features = pd.DataFrame(feature_rows)
    feature_names = [name for name in features.columns if name.startswith("staffing.")]
    distinct = features[feature_names].nunique()
    registry = pd.DataFrame(
        [
            {
                "feature": name,
                "family": families[name],
                "distinct_development_values": int(distinct[name]),
                "minimum": float(features[name].min()),
                "maximum": float(features[name].max()),
                "nonzero_fraction": float((features[name] != 0).mean()),
                "availability": "current_legal_observation",
                "status": "coverage_gap_constant" if distinct[name] <= 1 else "provisional_not_selected",
            }
            for name in feature_names
        ]
    )
    registry.to_csv(root / "reports/staffing_registry.csv", index=False)
    nonconstant = registry.loc[registry.distinct_development_values > 1, "feature"].tolist()
    correlations = []
    if nonconstant:
        corr = features[nonconstant].corr(method="spearman").to_numpy()
        correlations = [
            {"first": nonconstant[i], "second": nonconstant[j], "spearman": float(corr[i, j])}
            for i, j in zip(*np.where(np.triu(np.abs(corr) >= 0.995, k=1)), strict=True)
        ]
    pd.DataFrame(correlations, columns=["first", "second", "spearman"]).to_csv(
        root / "reports/staffing_correlations.csv", index=False
    )
    report = {
        "experiment": protocol["experiment"],
        "lineage": common,
        "protocol_sha256": digest(protocol),
        "games": len(rows),
        "identical_preterminal_blocks": len(prefix_counts),
        "seed_clusters": 2,
        "groups": frame.groupby(["opponent", "arm"]).mean(numeric_only=True).reset_index().to_dict("records"),
        "effects": effects.to_dict("records"),
        "artifact_manifest": manifests,
        "execution_seconds": total_seconds,
        "policy_latency_ms": {
            "median": float(np.median(latency)),
            "p95": float(np.quantile(latency, 0.95)),
            "max": float(max(latency)),
        },
        "screening": {
            "generated_features": FEATURE_COUNT,
            "screened_features": FEATURE_COUNT,
            "retained_for_final_model": 0,
            "rejected_for_final_model": 0,
            "sampled_development_observations": len(features),
            "families": dict(Counter(families.values())),
            "constant_features": registry.loc[registry.distinct_development_values <= 1, "feature"].tolist(),
            "high_spearman_pairs": len(correlations),
            "scope": "Mechanism activation, availability, variation and redundancy; not predictive selection",
        },
        "validation_or_holdout_used": False,
        "feature_completion_gate": "open_research",
        "limitations": [
            "Only two development seeds; intervals are descriptive and highly discrete",
            "One mirror-like opponent is deliberately a mechanism test, not population validation",
            "Only final-day routing is intervened; season-long multiworker coordination remains open",
            "The 53 staffing candidates are provisional and not selected predictors",
            "No leaderboard score or general win probability is inferred",
        ],
    }
    write_json(root / "reports/staffing_research.json", report)
    return report
