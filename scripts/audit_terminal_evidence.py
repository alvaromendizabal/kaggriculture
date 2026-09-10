"""Recompute saved legal traces and check evaluator-only resource/bound truth."""

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_livestock.audit import accounting
from kaggriculture_livestock.features import livestock_features, product_totals
from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.features import PUBLIC_FIELDS, observe_features
from kaggriculture_research.market_features import market_features
from kaggriculture_research.market_history import (
    BOUNDED_PRODUCTS,
    MarketHistory,
    own_nonbuyable_sales,
)
from kaggriculture_research.progress import Progress
from kaggriculture_research.relationship_features import CausalHistory, relationship_features
from kaggriculture_terminal.experiment import job_plan, validate_episode
from kaggriculture_terminal.policy import TerminalPolicy
from kaggriculture_terminal.routing import terminal_features


def replay(payload: dict) -> dict:
    seat, arm = payload["summary"]["seat"], payload["summary"]["arm"]
    policy, causal, history = TerminalPolicy(arm), CausalHistory(), MarketHistory()
    records = {(r["player"], r["observation"]["step"]): r for r in payload["records"]}
    samples = {s["step"]: s["values"] for s in payload["feature_samples"]}
    counters, actions, previous_sales = Counter(), [], None
    for step in range(719):
        record = records[seat, step]
        obs, action = record["observation"], record["action"]
        if set(obs) != set(PUBLIC_FIELDS):
            raise ValueError("Unexpected observation fields")
        before = copy.deepcopy(obs)
        decision = policy(obs)
        if before != obs or decision != action or policy.last_diagnostics != record["diagnostics"]:
            raise ValueError("Deterministic policy replay differs")
        actions.append(action)
        past, market_past = causal.observe(obs), history.observe(obs)
        if step in samples:
            # Independent composition, not experiment.feature_bank.
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
            if schema != payload["feature_schema"] or len(values) != 1579:
                raise ValueError("Audit schema changed")
            np.testing.assert_allclose(
                [values[k] for k in payload["feature_columns"]], samples[step], rtol=0, atol=1e-12
            )
            counters["feature_vectors"] += 1
        # Truth is inspected only after replay, never supplied to either actor.
        rival = records[1 - seat, step]
        actual = product_totals(rival["observation"]["private"])
        for item in BOUNDED_PRODUCTS:
            if not 0 <= actual[item] <= history.upper[item]:
                raise ValueError("Public history stock bound excluded evaluator truth")
            counters["stock_checks"] += 1
            if step:
                row = history.rows[-1][item]
                if not row["sales_lower"] <= previous_sales[item] <= row["sales_upper"]:
                    raise ValueError("Public history sales interval excluded truth")
                counters["sale_checks"] += 1
        previous_sales = own_nonbuyable_sales(rival["observation"], rival["action"])
        history.record_action(action)
        if step % 24 == 0 or step == 718:
            policy = TerminalPolicy.from_state_dict(policy.state_dict())
            history = MarketHistory.from_json(history.to_json())
            counters["state_restores"] += 1
        counters["callbacks"] += 1
    recomputed = accounting(payload)
    if recomputed != payload["accounting"]:
        raise ValueError("Independent resource replay differs from saved accounting")
    for key, value in recomputed["players"][seat].items():
        if value != payload["summary"].get(key):
            raise ValueError("Published summary differs from resource replay")
    counters["private_transitions"] = recomputed["transitions"]
    counters["product_balances"] = 18
    return {
        "counts": dict(counters),
        "actions_sha256": digest(actions),
        "episode_semantic_sha256": payload["semantic_sha256"],
        "mismatches": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--max-new-games", type=int, default=2)
    parser.add_argument("--uploads", type=Path)
    args = parser.parse_args()
    if not 1 <= args.max_new_games <= 48:
        raise ValueError("Audit batch size must be in 1..48")
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/terminal_research.json").read_text())
    common, jobs = job_plan(root, protocol)
    ready = None
    if args.uploads:
        from run_terminal_research import upload_callback

        ready = upload_callback(root, args.uploads)
    totals, rows, manifests, new = Counter(), [], [], 0
    progress = Progress()
    for job in jobs:
        path = root / job["path"]
        payload = load_checkpoint(path, job["lineage"])
        if payload is None:
            if args.partial:
                break
            raise ValueError("Research game missing")
        validate_episode(payload, job["key"])
        lineage = {
            "study_sha256": digest(common),
            "episode_sha256": file_digest(path),
            "audit_code_sha256": file_digest(Path(__file__)),
        }
        cached_path = root / "artifacts/terminal_audits" / (digest(lineage) + ".json.gz")
        result = load_checkpoint(cached_path, lineage)
        if result is None:
            if new >= args.max_new_games:
                break
            with progress.stage("audit_terminal_" + "_".join(map(str, job["key"].values()))):
                result = replay(payload)
                save_checkpoint(cached_path, lineage, result)
                new += 1
        if ready:
            ready(cached_path)
        totals.update(result["counts"])
        rows.append(
            {
                **job["key"],
                "actions_sha256": result["actions_sha256"],
                "episode_semantic_sha256": result["episode_semantic_sha256"],
            }
        )
        manifests.append(
            {
                "path": cached_path.relative_to(root).as_posix(),
                "sha256": file_digest(cached_path),
                "lineage": lineage,
            }
        )
    pd.DataFrame(rows).to_csv(root / "reports/terminal_action_identities.csv", index=False)
    result = {
        "games_audited": len(rows),
        "complete": len(rows) == 48,
        "study_sha256": digest(common),
        "audit_code_sha256": file_digest(Path(__file__)),
        "counts": dict(totals),
        "mismatches": 0,
        "artifacts": manifests,
        "new_audits": new,
        "reused_audits": len(rows) - new,
    }
    write_json(root / "reports/terminal_integrity.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "artifacts"}))


if __name__ == "__main__":
    main()
