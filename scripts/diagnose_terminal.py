"""Postregistration descriptive diagnostics; no new outcomes or policy tuning."""

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.relationship_features import ready_units
from kaggriculture_terminal.experiment import job_plan, validate_episode


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    _, jobs = job_plan(root, protocol)
    rows, latency, feature_times = [], [], []
    for job in jobs:
        payload = load_checkpoint(root / job["path"], job["lineage"])
        if payload is None:
            raise ValueError("Diagnostics require all registered games")
        validate_episode(payload, job["key"])
        seat = job["key"]["seat"]
        records = [r for r in payload["records"] if r["player"] == seat]
        if payload["preterminal_sha256"] != digest(
            [r for r in payload["records"] if r["observation"]["step"] < 696]
        ):
            raise ValueError("Preterminal hash does not match actual saved records")
        final = payload["evaluator_terminal_observations"][seat]
        start = records[696]["observation"]["farms"][seat]["money"]
        rows.append(
            {
                **job["key"],
                "preterminal_sha256": payload["preterminal_sha256"],
                "final_day_coin_gain": payload["rewards"][seat] - start,
                "terminal_feed": payload["summary"]["terminal_feed"],
                "terminal_noops": payload["summary"]["terminal_noops"],
                "residual_product_units": payload["summary"]["residual_product_units"],
                "terminal_water": payload["summary"]["terminal_water"],
                "terminal_pass": payload["summary"]["terminal_pass"],
                "terminal_worker_max": max(
                    1 + len(r["observation"]["farms"][seat]["hands"]) for r in records[696:]
                ),
                "terminal_hire_orders": sum(
                    o[0] == "HIRE" for r in records[696:] for o in r["action"]["market"]
                ),
                "unharvested_ready_units": sum(
                    ready_units(t, 29) for row in final["farms"][seat]["tiles"] for t in row
                ),
            }
        )
        latency.extend(payload["latency_ms"][696:])
        feature_times.extend(
            t
            for t, s in zip(
                payload["feature_extraction_ms"], payload["feature_samples"], strict=True
            )
            if s["step"] >= 696
        )
    frame = pd.DataFrame(rows)
    if not (frame.groupby(["seed", "seat", "opponent"]).preterminal_sha256.nunique() == 1).all():
        raise ValueError("Arms differ before the registered final-day intervention")
    registry = pd.read_csv(root / "reports/terminal_registry.csv")
    fresh = registry[registry.feature.str.startswith("terminal.")]
    summary = json.loads((root / "reports/terminal_research.json").read_text())
    result = {
        "scope": "postregistration descriptive mechanisms; not extra confirmatory tests",
        "new_features": len(fresh),
        "new_varying_features": int((fresh.distinct_development_values > 1).sum()),
        "new_constant_features": fresh.loc[
            fresh.distinct_development_values <= 1, "feature"
        ].tolist(),
        "jointly_screened_features": 1579,
        "project_union": 1621,
        "excluded_cash_features": 42,
        "assignment_activation_scope": (
            "Joint arm has one final-day worker because it does not rehire after overnight expiry. "
            "Its ablation is liquidation plus staffing, not multiworker assignment benefit. "
            "Multiworker route features are observed in baseline/feed trajectories only."
        ),
        "rows": rows,
        "groups": frame.drop(columns=["seed", "seat", "preterminal_sha256"])
        .groupby(["opponent", "arm"])
        .mean()
        .reset_index()
        .to_dict("records"),
        "terminal_policy_latency_ms": {
            "median": float(np.median(latency)),
            "p95": float(np.quantile(latency, 0.95)),
            "max": max(latency),
        },
        "terminal_feature_assembly_ms": {
            "p95": float(np.quantile(feature_times, 0.95)),
            "max": max(feature_times),
        },
        "timing_scope": (
            "local CPU; feature assembly excludes history updates, I/O and serialization"
        ),
        "registered_execution_seconds": summary["execution_seconds"],
        "source_sha256": file_digest(Path(__file__)),
    }
    write_json(root / "reports/terminal_diagnostics.json", result)
    integrity = json.loads((root / "reports/terminal_integrity.json").read_text())
    if integrity["games_audited"] != 48 or not integrity["complete"]:
        raise ValueError("Audit archive requires all 48 independently verified games")
    archive = root / "artifacts/terminal_audits.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
        for artifact in integrity["artifacts"]:
            path = root / artifact["path"]
            if file_digest(path) != artifact["sha256"]:
                raise ValueError("Audit cache differs")
            output.writestr(
                zipfile.ZipInfo(artifact["path"], date_time=(2026, 9, 10, 0, 0, 0)),
                path.read_bytes(),
            )
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "groups")}))


if __name__ == "__main__":
    main()
