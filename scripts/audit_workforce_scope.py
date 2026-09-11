"""Probe legal workforce scale in the pinned engine, without evaluating a season.

Two two-transition mechanics fixtures exercise both seats. No final game reward,
training labels, validation/holdout episodes, or Kaggle rank are used or reported.
"""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from kaggriculture_research.artifacts import write_json
from kaggriculture_research.environment import engine_manifest, game, make_environment
from kaggriculture_research.market_features import project_observation
from kaggriculture_staffing.features import WORKER_SLOTS


def probe() -> dict:
    records = []
    for hiring_player in (0, 1):
        env = make_environment(0)
        starting = float(env.state[hiring_player].observation.farms[hiring_player]["money"])
        counts = []
        for order_count in (4, 8):
            actions = []
            for player in (0, 1):
                farm = env.state[player].observation.farms[player]
                actions.append({
                    "farmer": ["PASS"],
                    "hands": [["PASS"] for _ in farm["hands"]],
                    "market": [["HIRE"] for _ in range(order_count)]
                    if player == hiring_player else [],
                })
            env.step(actions)
            counts.append(len(env.state[hiring_player].observation.farms[hiring_player]["hands"]))
        final = env.state[hiring_player].observation.farms[hiring_player]
        rejections = []
        for viewer in (0, 1):
            observation = dict(env.state[viewer].observation)
            try:
                project_observation(observation)
            except ValueError as error:
                rejections.append({"viewer": viewer, "rejected": True, "reason": str(error)})
            else:
                rejections.append({"viewer": viewer, "rejected": False, "reason": None})
        cost = sum(game._hire_cost(index) for index in range(12))
        if counts != [4, 12] or starting - float(final["money"]) != cost:
            raise ValueError("Workforce transition or exact hire-cost expectation failed")
        if not all(row["rejected"] for row in rejections):
            raise ValueError("The fixed-schema coverage boundary changed; inspect before recording")
        records.append({
            "hiring_player": hiring_player,
            "hire_orders_by_transition": [4, 8],
            "hired_hands_after_transitions": counts,
            "starting_money": starting,
            "remaining_money": float(final["money"]),
            "total_hiring_cost": cost,
            "current_extractor_views": rejections,
        })
    return {
        "status": "WORKFORCE_SCOPE_GAP_CONFIRMED",
        "engine": engine_manifest(),
        "controlled_fixture_seed": 0,
        "fixture_transitions": 4,
        "complete_games_run": 0,
        "training_or_holdout_used": False,
        "official_metric_effect_measured": False,
        "existing_staffing_feature_worker_slots": WORKER_SLOTS,
        "maximum_hired_hands_demonstrated": 12,
        "actual_game_maximum_claimed": False,
        "records": records,
        "feature_completion_gate": "open_research",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    report = probe()
    if args.record:
        root = Path(__file__).resolve().parents[1]
        report.update({
            "recorded_at_utc": datetime.now(UTC).isoformat(),
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "checkout_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "execution_environment": "GitHub Actions" if os.environ.get("GITHUB_ACTIONS")
            else "local",
        })
        write_json(root / "reports/workforce_scope_audit.json", report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
