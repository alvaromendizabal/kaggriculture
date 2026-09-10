"""Verify study 3 outcomes, source lineage and independent private-trace audit."""

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_research.environment import engine_manifest, game
from kaggriculture_research.market_experiment import factorial_summary
from kaggriculture_research.market_policy import FACTORS


def verify_markets(root: Path) -> dict:
    report = json.loads((root / "reports/market_research.json").read_text())
    protocol = json.loads((root / "configs/market_research.json").read_text())
    foundation = json.loads((root / "configs/research.json").read_text())
    if digest(protocol) != report["protocol_sha256"] or protocol != report["lineage"]["protocol"]:
        raise ValueError("Market experiment protocol changed")
    if set(protocol["development_seeds"]) & set(
        foundation["development_seeds"]
        + foundation["validation_seeds"]
        + foundation["holdout_seeds"]
    ):
        raise ValueError("Market seed boundary changed")
    if engine_manifest() != report["lineage"]["engine"]:
        raise ValueError("Market engine changed")
    for name, sha in report["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != sha:
            raise ValueError(f"Market result is stale for {name}")
    for name, expected_sha in protocol["frozen_sources"].items():
        if expected_sha != report["lineage"]["code"][name]:
            raise ValueError("Frozen reference lineage changed")
    frame = pd.read_csv(root / "reports/market_games.csv", dtype={"arm": str})
    expected = set(product(protocol["development_seeds"], protocol["seats"], protocol["arms"]))
    if (
        len(frame) != 48
        or set(frame[["seed", "seat", "arm"]].itertuples(index=False, name=None)) != expected
    ):
        raise ValueError("Incomplete or duplicated factorial design")
    for i, factor in enumerate(FACTORS):
        if not (frame[factor] == frame.arm.str[i].astype(int)).all():
            raise ValueError("Factor label differs from arm")
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Non-finite market outcome")
    if not frame.match_score.isin([0, 0.5, 1]).all():
        raise ValueError("Invalid local match score")
    expected_score = (frame.coin_margin > 0).astype(float) + 0.5 * (frame.coin_margin == 0)
    if not (frame.match_score == expected_score).all():
        raise ValueError("Outcome score and margin disagree")
    if not (
        frame.harvested_units
        == frame.sold_units + frame.unsold_product_units + frame.discarded_units
    ).all():
        raise ValueError("Market product conservation failed")
    if report["conservation_verified_games"] != 48 or report["games"] != 48:
        raise ValueError("Market game count differs")
    if report["validation_or_holdout_used"] or report["feature_completion_gate"] != "closed":
        raise ValueError("Feature completion boundary changed")
    effects = factorial_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    for published in (
        pd.DataFrame(report["effects"]),
        pd.read_csv(root / "reports/market_effects.csv"),
    ):
        pd.testing.assert_frame_equal(
            effects, published, check_dtype=False, check_like=True, atol=1e-9, rtol=0
        )
    groups = (
        frame.groupby("arm").mean(numeric_only=True).drop(columns=["seed", "seat"]).reset_index()
    )
    pd.testing.assert_frame_equal(
        groups,
        pd.DataFrame(report["groups"]),
        check_dtype=False,
        check_like=True,
        atol=1e-9,
        rtol=0,
    )
    registry = pd.read_csv(root / "reports/market_registry.csv")
    screening = report["screening"]
    if len(registry) != 933 or registry.feature.nunique() != 933:
        raise ValueError("Market feature registry schema changed")
    if registry.family.value_counts().to_dict() != screening["families"]:
        raise ValueError("Feature family counts differ")
    if screening["sampled_development_observations"] != 48 * 181:
        raise ValueError("Sampled development coverage differs")
    if screening["generated_features"] != 933 or screening["screened_features"] != 933:
        raise ValueError("Reported feature screening count differs")
    if screening["retained_for_final_model"] != 0 or screening["rejected_for_final_model"] != 0:
        raise ValueError("Descriptive screen was presented as final selection")
    constants = set(registry.loc[registry.distinct_development_values <= 1, "feature"])
    if constants != set(screening["constant_features"]):
        raise ValueError("Constant-feature evidence differs")
    correlations = pd.read_csv(root / "reports/market_correlations.csv")
    if len(correlations) != screening["high_spearman_pairs"]:
        raise ValueError("Correlation audit count differs")
    if not correlations.spearman.abs().between(0.995 - 1e-12, 1 + 1e-12).all():
        raise ValueError("Correlation audit threshold differs")
    cloud = json.loads((root / "reports/market_cloud_verification.json").read_text())
    if cloud["run"]["status"] != "completed" or any(
        s["status"] != "passed" for s in cloud["run"]["steps"]
    ):
        raise ValueError("AWS execution did not finish successfully")
    manifest = {a["path"]: a for a in cloud["run"]["artifacts"]}
    for name in (
        "market_games.csv",
        "market_effects.csv",
        "market_research.json",
        "market_registry.csv",
        "market_correlations.csv",
    ):
        relative = "reports/" + name
        if file_digest(root / relative) != manifest[relative]["sha256"]:
            raise ValueError(f"Published result differs from its AWS execution: {name}")
    if len(report["artifact_manifest"]) != 48:
        raise ValueError("Episode artifact manifest is incomplete")
    for artifact in [*report["artifact_manifest"], screening["matrix_artifact"]]:
        if artifact["sha256"] != manifest[artifact["path"]]["sha256"]:
            raise ValueError("Private episode/matrix artifact differs from the AWS manifest")
    integrity = json.loads((root / "reports/market_integrity.json").read_text())
    if integrity["audit_code_sha256"] != file_digest(root / "scripts/audit_market_evidence.py"):
        raise ValueError("Independent evidence audit source changed")
    if integrity["experiment_report_sha256"] != file_digest(root / "reports/market_research.json"):
        raise ValueError("Independent evidence audit refers to a different experiment")
    if integrity["episode_manifest_sha256"] != digest(report["artifact_manifest"]):
        raise ValueError("Independent audit episode lineage changed")
    if (
        integrity["games_verified"],
        integrity["candidate_callback_observations_verified"],
        integrity["sampled_feature_vectors_recomputed"],
        integrity["features_per_vector"],
    ) != (48, 48 * 719, 48 * 181, 933):
        raise ValueError("Independent evidence coverage is incomplete")
    behavior_path = root / "reports/market_behavior.csv"
    if integrity["behavior_csv_sha256"] != file_digest(behavior_path):
        raise ValueError("Post-hoc behavior summary changed")
    behavior = pd.read_csv(behavior_path, dtype={"arm": str})
    behavior_keys = ["seed", "seat", "arm", "product"]
    expected_behavior = {(*block, crop) for block in expected for crop in game.CROPS}
    if (
        len(behavior) != len(expected_behavior)
        or set(behavior[behavior_keys].itertuples(index=False, name=None)) != expected_behavior
    ):
        raise ValueError("Post-hoc behavior design is incomplete")
    totals = behavior.groupby(["seed", "seat", "arm"]).candidate_units_sold.sum()
    outcome_totals = frame.set_index(["seed", "seat", "arm"]).sold_units.reindex(totals.index)
    if not (totals == outcome_totals).all():
        raise ValueError("Product-level sales disagree with game-level conservation")
    computed_lead = behavior.opponent_first_sale_step - behavior.candidate_first_sale_step
    if not np.allclose(computed_lead, behavior.candidate_first_sale_lead_actions, equal_nan=True):
        raise ValueError("First-sale timing contrast differs")
    hold = json.loads((root / "reports/market_hold_analysis.json").read_text())
    for field, relative in (
        ("analysis_code_sha256", "scripts/analyze_market_holds.py"),
        ("diagnostics_csv_sha256", "reports/market_hold_diagnostics.csv"),
        ("experiment_report_sha256", "reports/market_research.json"),
    ):
        if hold[field] != file_digest(root / relative):
            raise ValueError("Post-hoc holding analysis lineage changed")
    if hold["episode_manifest_sha256"] != digest(report["artifact_manifest"]):
        raise ValueError("Holding analysis used different episodes")
    holds = pd.read_csv(root / "reports/market_hold_diagnostics.csv", dtype={"arm": str})
    if len(holds) != 343 or holds.duplicated(["seed", "seat", "arm", "step", "product"]).any():
        raise ValueError("Holding event coverage changed")
    if not (holds.held_units > 0).all() or not holds.step.between(0, 717).all():
        raise ValueError("Invalid held-stock event")
    if not (holds.quote_change == holds.quote_next_callback - holds.quote_before).all():
        raise ValueError("Holding price-change diagnostic differs")
    groups = []
    for arm, group in holds.groupby("arm"):
        groups.append(
            {
                "arm": arm,
                "product_hold_events": len(group),
                "same_product_rival_sale_events": int((group.same_turn_rival_sale_units > 0).sum()),
                "next_quote_fall_events": int((group.quote_change < 0).sum()),
                "next_quote_rise_events": int((group.quote_change > 0).sum()),
                "mean_next_quote_change": float(group.quote_change.mean()),
            }
        )
    if groups != hold["groups"]:
        raise ValueError("Holding diagnostic summary differs from event data")
    return cloud


if __name__ == "__main__":
    verify_markets(Path(__file__).resolve().parents[1])
    print("Verified market study: 48 games, 933 descriptors and replay audit.")
