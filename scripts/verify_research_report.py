"""Verify all three studies without rerunning 192 unchanged development games.

The original simulator runs and notebook execution occurred on AWS. CI
independently runs mechanics/determinism tests, checks source and protocol lineage,
recomputes statistics from all 192 public outcome rows, and validates the
executed notebook. Raw trajectory checkpoints remain private in S3.
"""

import ast
import json
from itertools import product
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from notebook_provenance import archived_study_sources
from verify_market_report import verify_markets

from kaggriculture_research.artifacts import digest, file_digest
from kaggriculture_research.environment import engine_manifest, game
from kaggriculture_research.experiment import paired_summary
from kaggriculture_research.relationship_experiment import factorial_summary
from kaggriculture_research.relationship_policy import FACTORS


def verify_relationships(root: Path) -> dict:
    report = json.loads((root / "reports/relationship_research.json").read_text())
    protocol = json.loads((root / "configs/relationship_research.json").read_text())
    foundation = json.loads((root / "configs/research.json").read_text())
    if digest(protocol) != report["protocol_sha256"] or protocol != report["lineage"]["protocol"]:
        raise ValueError("Relationship experiment protocol changed")
    if protocol["development_seeds"] != foundation["development_seeds"]:
        raise ValueError("Relationship seed boundary changed")
    if engine_manifest() != report["lineage"]["engine"]:
        raise ValueError("Relationship engine changed")
    for name, sha in report["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != sha:
            raise ValueError(f"Relationship result is stale for {name}")
    if protocol["frozen_crop_policy_sha256"] != report["lineage"]["code"]["crop_policy.py"]:
        raise ValueError("Frozen opponent lineage changed")
    frame = pd.read_csv(root / "reports/relationship_games.csv", dtype={"arm": str})
    expected = set(product(protocol["development_seeds"], protocol["seats"], protocol["arms"]))
    if (
        len(frame) != 64
        or set(frame[["seed", "seat", "arm"]].itertuples(index=False, name=None)) != expected
    ):
        raise ValueError("Incomplete or duplicated factorial design")
    for i, factor in enumerate(FACTORS):
        if not (frame[factor] == frame.arm.str[i].astype(int)).all():
            raise ValueError("Factor label differs from arm")
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Non-finite relationship outcome")
    if not frame.match_score.isin([0, 0.5, 1]).all():
        raise ValueError("Invalid local match score")
    expected_score = (frame.coin_margin > 0).astype(float) + 0.5 * (frame.coin_margin == 0)
    if not (frame.match_score == expected_score).all():
        raise ValueError("Outcome score and margin disagree")
    if not (
        frame.harvested_units
        == frame.sold_units + frame.unsold_product_units + frame.discarded_units
    ).all():
        raise ValueError("Relationship product conservation failed")
    if report["conservation_verified_games"] != 64 or report["games"] != 64:
        raise ValueError("Relationship game count differs")
    if report["validation_or_holdout_used"] or report["feature_completion_gate"] != "closed":
        raise ValueError("Feature completion boundary changed")
    effects = factorial_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    for published in (
        pd.DataFrame(report["effects"]),
        pd.read_csv(root / "reports/relationship_effects.csv"),
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
    registry = pd.read_csv(root / "reports/relationship_registry.csv")
    screening = report["screening"]
    if len(registry) != 618 or registry.feature.nunique() != 618:
        raise ValueError("Relationship feature registry schema changed")
    if registry.family.value_counts().to_dict() != screening["families"]:
        raise ValueError("Feature family counts differ")
    if screening["sampled_development_observations"] != 64 * 181:
        raise ValueError("Sampled development coverage differs")
    if screening["generated_features"] != 618 or screening["screened_features"] != 618:
        raise ValueError("Reported feature screening count differs")
    if screening["retained_for_final_model"] != 0 or screening["rejected_for_final_model"] != 0:
        raise ValueError("Descriptive screen was presented as final selection")
    constants = set(registry.loc[registry.distinct_development_values <= 1, "feature"])
    if constants != set(screening["constant_features"]):
        raise ValueError("Constant-feature evidence differs")
    correlations = pd.read_csv(root / "reports/relationship_correlations.csv")
    if len(correlations) != screening["high_spearman_pairs"]:
        raise ValueError("Correlation audit count differs")
    if not correlations.spearman.abs().between(0.995 - 1e-12, 1 + 1e-12).all():
        raise ValueError("Correlation audit threshold differs")
    cloud = json.loads((root / "reports/relationship_cloud_verification.json").read_text())
    if cloud["run"]["status"] != "completed" or any(
        s["status"] != "passed" for s in cloud["run"]["steps"]
    ):
        raise ValueError("AWS execution did not finish successfully")
    manifest = {a["path"]: a for a in cloud["run"]["artifacts"]}
    for name in (
        "relationship_games.csv",
        "relationship_effects.csv",
        "relationship_research.json",
        "relationship_registry.csv",
        "relationship_correlations.csv",
    ):
        relative = "reports/" + name
        if file_digest(root / relative) != manifest[relative]["sha256"]:
            raise ValueError(f"Published result differs from its AWS execution: {name}")
    if len(report["artifact_manifest"]) != 64:
        raise ValueError("Episode artifact manifest is incomplete")
    for artifact in [*report["artifact_manifest"], screening["matrix_artifact"]]:
        if artifact["sha256"] != manifest[artifact["path"]]["sha256"]:
            raise ValueError("Private episode/matrix artifact differs from the AWS manifest")
    integrity = json.loads((root / "reports/relationship_integrity.json").read_text())
    if integrity["audit_code_sha256"] != file_digest(
        root / "scripts/audit_relationship_evidence.py"
    ):
        raise ValueError("Independent evidence audit source changed")
    if integrity["experiment_report_sha256"] != file_digest(
        root / "reports/relationship_research.json"
    ):
        raise ValueError("Independent evidence audit refers to a different experiment")
    if integrity["episode_manifest_sha256"] != digest(report["artifact_manifest"]):
        raise ValueError("Independent audit episode lineage changed")
    if (
        integrity["games_verified"],
        integrity["candidate_callback_observations_verified"],
        integrity["sampled_feature_vectors_recomputed"],
        integrity["features_per_vector"],
    ) != (64, 64 * 719, 64 * 181, 618):
        raise ValueError("Independent evidence coverage is incomplete")
    behavior_path = root / "reports/relationship_behavior.csv"
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
    return cloud


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "reports/feature_research.json").read_text())
    protocol = json.loads((root / "configs/feature_research.json").read_text())
    if digest(protocol) != report["protocol_sha256"] or protocol != report["lineage"]["protocol"]:
        raise ValueError("Report protocol differs from the registered experiment")
    if engine_manifest() != report["lineage"]["engine"]:
        raise ValueError("Report engine differs from the pinned installation")
    for name, sha in report["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != sha:
            raise ValueError(f"Report is stale for {name}")
    frame = pd.read_csv(root / "reports/feature_games.csv")
    columns = ["seed", "seat", "opponent", "variant"]
    expected = set(
        product(
            protocol["development_seeds"],
            protocol["seats"],
            protocol["opponents"],
            protocol["variants"],
        )
    )
    if len(frame) != 80 or set(frame[columns].itertuples(index=False, name=None)) != expected:
        raise ValueError("Incomplete or duplicated paired design")
    if report["validation_or_holdout_used"] or report["feature_completion_gate"] != "closed":
        raise ValueError("Research boundary changed")
    computed = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    pd.testing.assert_frame_equal(
        computed,
        pd.DataFrame(report["paired_results"]),
        check_dtype=False,
        check_like=True,
        atol=1e-9,
        rtol=0,
    )
    pd.testing.assert_frame_equal(
        computed,
        pd.read_csv(root / "reports/feature_ablations.csv"),
        check_dtype=False,
        atol=1e-9,
        rtol=0,
    )
    if not np.isfinite(frame.select_dtypes(include="number").to_numpy()).all():
        raise ValueError("Non-finite outcome")
    behavior = pd.read_csv(root / "reports/feature_behavior.csv")
    joined = frame.merge(behavior, on=columns, validate="one_to_one")
    if (
        len(joined) != 80
        or not (
            joined.harvested_units
            == joined.sold_units + joined.unsold_product_units + joined.discarded_units
        ).all()
    ):
        raise ValueError("Published product conservation failed")
    audit = json.loads((root / "reports/feature_behavior_audit.json").read_text())
    if file_digest(root / "scripts/audit_feature_behavior.py") != audit["audit_code_sha256"]:
        raise ValueError("Behavior audit source changed")
    notebook = nbformat.read(root / "notebooks/02_feature_research.ipynb", as_version=4)
    cloud = verify_relationships(root)
    latest_cloud = verify_markets(root)
    recorded = next(
        a
        for a in latest_cloud["run"]["artifacts"]
        if a["path"] == "notebooks/02_feature_research.ipynb"
    )
    extended = any(c.id.startswith("supply-") for c in notebook.cells)
    if not extended and file_digest(root / recorded["path"]) != recorded["sha256"]:
        raise ValueError("Notebook differs from its executed AWS artifact")
    nbformat.validate(notebook)
    cells = [
        cell
        for cell in notebook.cells
        if cell.cell_type == "code" and not cell.id.startswith(("supply-", "livestock-"))
    ]
    if len(cells) != 17:
        raise ValueError("Unexpected research notebook structure")
    sources = archived_study_sources(cells, require_migration=extended)
    prior_cells = [
        source
        for cell, source in zip(cells, sources, strict=True)
        if not cell.id.startswith(("relationships-", "markets-"))
    ]
    if (
        len(prior_cells) != 7
        or digest(prior_cells) != cloud["verification"]["preserved_study1_code_sha256"]
    ):
        raise ValueError("Original study notebook code changed")
    previous = [
        source
        for cell, source in zip(cells, sources, strict=True)
        if not cell.id.startswith("markets-")
    ]
    if (
        len(previous) != 12
        or digest(previous) != latest_cloud["verification"]["preserved_studies12_code_sha256"]
    ):
        raise ValueError("Earlier notebook study code changed")
    for cell in cells:
        ast.parse(cell.source)
        if cell.execution_count is None:
            raise ValueError("Research notebook has an unexecuted cell")
        if any(
            o.output_type == "error" or (o.output_type == "stream" and o.name == "stderr")
            for o in cell.outputs
        ):
            raise ValueError("Research notebook contains execution errors")
    print("Verified three studies: 192 outcomes, lineage, contrasts, conservation and notebook.")


if __name__ == "__main__":
    main()
