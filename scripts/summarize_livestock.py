"""Report frozen episodes; absent optional action counters mean zero events.

The original preregistered simulator/policy sources remain immutable. This
reporting adapter uses the same paired estimator and screen, normalizing absent
Counter keys before grouping; it does not alter trajectories or primary metrics.
"""

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_livestock.experiment import METRICS, job_plan, paired_summary, validate_episode
from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.progress import Progress


def outcome_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    counters = [c for c in frame if c.startswith("commands_")]
    frame[counters] = frame[counters].fillna(0)
    if not set(METRICS) <= set(frame) or not np.isfinite(frame[list(METRICS)].to_numpy()).all():
        raise ValueError("Missing or nonfinite registered outcome")
    return frame


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
    frame = outcome_frame(rows)
    frame.to_csv(root / "reports/livestock_games.csv", index=False)
    effects = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    effects.to_csv(root / "reports/livestock_effects.csv", index=False)
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
    pd.DataFrame(registry).to_csv(root / "reports/livestock_registry.csv", index=False)
    corr = data[nonconstant].corr(method="spearman").to_numpy()
    correlations = [
        {"first": nonconstant[i], "second": nonconstant[j], "spearman": float(corr[i, j])}
        for i, j in zip(*np.where(np.triu(np.abs(corr) >= 0.995, k=1)), strict=True)
    ]
    pd.DataFrame(correlations, columns=["first", "second", "spearman"]).to_csv(
        root / "reports/livestock_correlations.csv", index=False
    )
    matrix_lineage = {
        "study_sha256": digest(common),
        "schema": schema,
        "metadata_sha256": digest(metadata),
        "matrix_sha256": digest(matrix),
    }
    matrix_path = root / "artifacts/livestock_features" / (digest(matrix_lineage) + ".json.gz")
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
        "reporting_adapter_sha256": file_digest(Path(__file__)),
        "optional_absent_command_counters": "zero_events",
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
            "Two fixed opponents do not represent the competition population",
            "Fertilizer rollouts assume fixed tile continuation and current quote curves",
            "The 42 prior cash-bound features are excluded because this policy buys products",
            "Same initial seed does not fix future shops after policy-induced RNG divergence",
            "Sequential ablations are conditional effects, not factorial main effects",
            "Land, routing, worker assignment, herd layouts and opponent diversity remain open",
        ],
    }
    write_json(root / "reports/livestock_research.json", report)
    return report


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    with Progress().stage("livestock_summary_and_joint_feature_screen"):
        result = summarize(root, protocol)
    print(
        json.dumps(
            {"games": result["games"], "features": result["screening"]["generated_features"]}
        )
    )
