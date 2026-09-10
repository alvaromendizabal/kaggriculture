"""Observation coverage, descriptive profiling, and honest foundation status."""

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest, save_checkpoint, write_json
from kaggriculture_research.environment import engine_manifest
from kaggriculture_research.features import observe_features


def audit_episodes(root: Path, episodes: list[dict[str, Any]], protocol: dict) -> dict[str, Any]:
    vectors, snapshots, games, families = [], [], [], {}
    latencies = []
    for episode in episodes:
        seat = episode["starter_seat"]
        games.append(
            {
                k: episode[k]
                for k in (
                    "seed",
                    "starter_seat",
                    "starter_win",
                    "starter_tie",
                    "coin_margin",
                    "rewards",
                    "statuses",
                    "states",
                    "decision_steps",
                    "semantic_sha256",
                )
            }
        )
        for row in episode["observations"]:
            vector = observe_features(row["observation"])
            if families and families != vector.families:
                raise ValueError("Feature schema drift within the same experiment")
            families = vector.families
            vectors.append(vector.values)
            latencies.append(row["latency_ms"])
            if row["observation"]["hour"] == 0 and row["player"] == seat:
                snapshots.append(
                    {
                        "seed": episode["seed"],
                        "seat": seat,
                        "day": row["observation"]["day"],
                        "starter_cash": vector.values["own.cash"],
                        "cash_lead": vector.values["relative.cash_lead"],
                        "carrot_price": vector.values["market.CARROT.price"],
                        "carrot_demand": vector.values["demand.CARROT.current_daily_units"],
                    }
                )
    frame = pd.DataFrame(vectors)
    if not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Feature matrix contains missing or non-finite values")
    distinct = frame.nunique()
    constants = distinct[distinct <= 1].index.tolist()
    duplicate_groups: dict[str, list[str]] = {}
    for col in frame:
        if col not in constants:
            key = digest(frame[col].tolist())
            duplicate_groups.setdefault(key, []).append(col)
    duplicates = [g for g in duplicate_groups.values() if len(g) > 1]
    feature_lineage = {
        "engine": engine_manifest(),
        "episodes": [e["semantic_sha256"] for e in episodes],
        "feature_code": file_digest(Path(__file__).with_name("features.py")),
        "audit_code": file_digest(Path(__file__)),
        "protocol_sha256": digest(protocol),
    }
    feature_path = root / "artifacts/features" / (digest(feature_lineage) + ".json.gz")
    save_checkpoint(
        feature_path,
        feature_lineage,
        {"columns": list(frame), "families": families, "rows": frame.to_numpy().tolist()},
    )
    paired_scores = (
        pd.DataFrame(games)
        .assign(score=lambda x: x["starter_win"] + 0.5 * x["starter_tie"])
        .groupby("seed")["score"]
        .mean()
    )
    # The unit of independence is the seed; the two seats are paired, not independent.
    summary = {
        "milestone": "foundation_and_observation_audit",
        "purpose": protocol["purpose"],
        "engine": engine_manifest(),
        "feature_lineage": feature_lineage,
        "feature_artifact_sha256": file_digest(feature_path),
        "episodes": len(episodes),
        "independent_development_seeds": len(paired_scores),
        "callback_observations": len(frame),
        "games": games,
        "reference_match_score": float(paired_scores.mean()),
        "reference_win_rate": float(np.mean([g["starter_win"] for g in games])),
        "reference_tie_rate": float(np.mean([g["starter_tie"] for g in games])),
        "mean_reference_coin_margin": float(np.mean([g["coin_margin"] for g in games])),
        "official_leaderboard_rating": None,
        "candidate_features": len(frame.columns),
        "screened_for_selection": 0,
        "retained_for_model": 0,
        "rejected_for_model": 0,
        "family_counts": dict(Counter(families.values())),
        "constant_in_reference_rollouts": constants,
        "duplicate_groups_in_reference_rollouts": duplicates,
        "missing_values": int(frame.isna().sum().sum()),
        "feature_benefit_measured": False,
        "reference_policy_latency_ms": {
            "median": float(np.median(latencies)),
            "p99": float(np.quantile(latencies, 0.99)),
            "max": float(np.max(latencies)),
        },
        "holdout_used": False,
        "validation_used": False,
        "gate": {
            "feature_research_complete": False,
            "final_training_allowed": False,
            "reason": "No policy-driven feature screening or family ablations yet",
        },
        "limitations": [
            "Four seeds and two simple official policies do not support leaderboard conclusions.",
            "Constant and duplicate columns are coverage flags, not rejection decisions.",
            "Current-state candidates have not been consumed by a learned or planning policy.",
            "Coin margin is diagnostic; official ranking uses wins/losses/ties.",
            "Local call timing does not reproduce Kaggle's isolated submission runtime.",
        ],
    }
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    write_json(reports / "foundation.json", summary)
    pd.DataFrame(snapshots).to_csv(reports / "trajectories.csv", index=False)
    pd.DataFrame(
        [
            {
                "feature": name,
                "family": families[name],
                "distinct_values_in_reference": int(distinct[name]),
                "status": "candidate_unscreened",
                "availability": "current_agent_observation",
            }
            for name in frame
        ]
    ).to_csv(reports / "feature_registry.csv", index=False)
    return summary
