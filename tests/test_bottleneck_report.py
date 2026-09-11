"""Validate published measured evidence against its actual AWS byte receipts."""

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_published_data_matches_s3_readback_receipts():
    receipts = json.loads((ROOT / "reports/bottleneck_uploads.json").read_text())
    for name in ("reports/bottleneck_research.json", "reports/bottleneck_registry.csv"):
        data = (ROOT / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == receipts[name]["sha256"]
        assert len(data) == receipts[name]["bytes"]
        assert receipts[name]["readback_verified"] is True


def test_feature_audit_does_not_turn_coverage_into_performance_claim():
    report = json.loads((ROOT / "reports/bottleneck_research.json").read_text())
    assert report["new_games"] == 0
    assert report["final_selected_features"] == 0
    assert report["official_metric_effect_measured"] is False
    assert report["validation_or_holdout_used"] is False
    assert report["original_pilot_status"] == "HALTED_LATENCY_LIMIT"
    assert report["accepted_source_games"] == 7
    assert report["original_planned_games"] == 8
    assert report["feature_completion_gate"] == "open_research"
    assert report["observations"] == report["base_assignment_parity_states"] == 161
    with (ROOT / "reports/bottleneck_registry.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == report["candidate_columns"] == 39
    assert sum(int(row["distinct_values"]) > 1 for row in rows) == report["varying_columns"]
    assert report["varying_columns"] + report["constant_columns"] == len(rows)


def test_nonbinding_capacity_finding_matches_measured_registry():
    with (ROOT / "reports/bottleneck_registry.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    capacity = [r for r in rows if "capacity_" in r["feature"] and "utility_delta" in r["feature"]]
    assert len(capacity) == 6
    assert all(float(row["minimum"]) == float(row["maximum"]) == 0 for row in capacity)
