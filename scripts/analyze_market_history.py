"""Replay legal-history candidates on verified development traces, without new games.

Opponent-private quantities are evaluator-only labels checked AFTER extraction.
No label, opponent action or future record is passed to MarketHistory. This is an
identification/coverage study, not a policy ablation or held-out prediction test.
"""

import gzip
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.environment import engine_manifest
from kaggriculture_research.market_experiment import episode_hash
from kaggriculture_research.market_features import visible_wave
from kaggriculture_research.market_history import (
    BOUNDED_PRODUCTS,
    MarketHistory,
    own_nonbuyable_sales,
)
from kaggriculture_research.progress import Progress


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report_path = root / "reports/market_research.json"
    report = json.loads(report_path.read_text())
    if engine_manifest() != report["lineage"]["engine"]:
        raise ValueError("Interpreter differs from the source experiment")
    for name, expected in report["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != expected:
            raise ValueError(f"Previous study source changed: {name}")
    protocol = report["lineage"]["protocol"]
    expected_games = {
        (seed, seat, arm)
        for seed in protocol["development_seeds"]
        for seat in protocol["seats"]
        for arm in protocol["arms"]
    }
    observed_games = set()
    matrices, groups, latencies, state_sizes = [], [], [], []
    columns = families = None
    progress = Progress()
    with progress.stage("replay_legal_market_history"):
        for artifact in report["artifact_manifest"]:
            path = root / artifact["path"]
            if file_digest(path) != artifact["sha256"]:
                raise ValueError("Source trace checksum differs")
            with gzip.open(path, "rt") as stream:
                summary = json.load(stream)["payload"]["summary"]
            key = tuple(summary[k] for k in ("seed", "seat", "arm"))
            if key not in expected_games or key in observed_games:
                raise ValueError("Unexpected or repeated development game")
            lineage = {**report["lineage"], **{k: summary[k] for k in ("seed", "seat", "arm")}}
            payload = load_checkpoint(path, lineage)
            if payload is None or episode_hash(payload) != artifact["semantic_sha256"]:
                raise ValueError("Source episode lineage or semantic identity differs")
            records = {(r["player"], r["observation"]["step"]): r for r in payload["records"]}
            if len(records) != 1438:
                raise ValueError("Expected 719 observations for both players")
            history = MarketHistory()
            metrics = {item: defaultdict(int) for item in BOUNDED_PRODUCTS}
            vectors = []
            seat = summary["seat"]
            previous_rival_sales = None
            for step in range(719):
                record = records[seat, step]
                start = time.perf_counter()
                feature = history.observe(record["observation"])
                history.record_action(record["action"])
                latencies.append(1000 * (time.perf_counter() - start))
                if columns is None:
                    columns, families = sorted(feature.values), feature.families
                if sorted(feature.values) != columns or feature.families != families:
                    raise ValueError("History feature schema changed")
                vectors.append([feature.values[name] for name in columns])
                if step % 24 == 0 or step == 718:
                    serialized = history.to_json()
                    state_sizes.append(len(serialized.encode()))
                    history = MarketHistory.from_json(serialized)

                # Evaluator-only truth begins here, after the causal vector is fixed.
                rival_record = records[1 - seat, step]
                private = rival_record["observation"]["private"]
                visible = visible_wave(record["observation"], 1 - seat)
                for item, group in metrics.items():
                    group["callbacks"] += 1
                    stored = private["shed"].get(item, 0) + sum(
                        inv.get(item, 0) for inv in private["inventories"]
                    )
                    upper = feature.values[f"market_history.{item}.last.stock_upper"]
                    if not 0 <= stored <= upper:
                        raise ValueError(f"Rival {item} stock outside bound at {key}, step {step}")
                    group["stored_positive_callbacks"] += int(stored > 0)
                    group["upper_positive_callbacks"] += int(upper > 0)
                    group["empty_but_upper_positive_callbacks"] += int(stored == 0 and upper > 0)
                    group["stock_bound_exact_callbacks"] += int(stored == upper)
                    group["stock_upper_excess_sum"] += int(upper - stored)
                    group["stock_upper_excess_max"] = max(
                        group["stock_upper_excess_max"], int(upper - stored)
                    )
                    no_visible = sum(n for n, _ in visible[item]) == 0
                    group["stored_positive_without_visible_ready_callbacks"] += int(
                        stored > 0 and no_visible
                    )
                    if step:
                        lower = feature.values[f"market_history.{item}.last.sales_lower"]
                        sale_upper = feature.values[f"market_history.{item}.last.sales_upper"]
                        actual = previous_rival_sales[item]
                        if not lower <= actual <= sale_upper:
                            raise ValueError(
                                f"Rival {item} sales outside bound at {key}, step {step}"
                            )
                        group["transitions"] += 1
                        group["sale_bounds_exact_transitions"] += int(lower == sale_upper)
                        group["gross_sale_units"] += actual
                        group["positive_sale_transitions"] += int(actual > 0)
                        group["sale_lower_units"] += int(lower)
                        group["sale_bound_width_sum"] += int(sale_upper - lower)
                        group["floor_censored_transitions"] += int(
                            feature.values[f"market_history.{item}.last.floor_censored"]
                        )
                previous_rival_sales = own_nonbuyable_sales(
                    rival_record["observation"], rival_record["action"]
                )
            matrices.append(np.asarray(vectors, dtype="<f8"))
            groups.extend(
                {"seed": key[0], "seat": key[1], "arm": key[2], "product": item, **dict(group)}
                for item, group in metrics.items()
            )
            observed_games.add(key)
            progress.log(
                "game_replayed",
                "replay_legal_market_history",
                progress.started,
                completed_games=len(observed_games),
                expected_games=len(expected_games),
            )
    if observed_games != expected_games:
        raise ValueError("Development episode coverage is incomplete")
    matrix = np.concatenate(matrices)
    if not np.isfinite(matrix).all() or matrix.shape != (48 * 719, 333):
        raise ValueError("Unexpected feature matrix")
    constant = np.ptp(matrix, axis=0) == 0
    duplicate = defaultdict(list)
    registry = []
    for index, name in enumerate(columns):
        if not constant[index]:
            duplicate[hashlib.sha256(matrix[:, index].tobytes()).hexdigest()].append(name)
        registry.append(
            {
                "name": name,
                "family": families[name],
                "constant": bool(constant[index]),
                "minimum": float(matrix[:, index].min()),
                "maximum": float(matrix[:, index].max()),
                "decision": "provisional",
                "reason": "No policy ablation or out-of-seed predictive validation",
            }
        )
    totals = []
    for item in BOUNDED_PRODUCTS:
        subset = [row for row in groups if row["product"] == item]
        fields = set(subset[0]) - {"seed", "seat", "arm", "product"}
        totals.append(
            {
                "product": item,
                **{
                    field: max(r[field] for r in subset)
                    if field.endswith("_max")
                    else sum(r[field] for r in subset)
                    for field in sorted(fields)
                },
            }
        )
    result = {
        "study": "legal-market-history-identification-v1",
        "scope": "Post-hoc development replay; not a policy-performance experiment",
        "games_reused": 48,
        "new_games": 0,
        "callback_vectors": len(matrix),
        "candidate_features": matrix.shape[1],
        "screened_features": matrix.shape[1],
        "constant_features": int(constant.sum()),
        "varying_features": int((~constant).sum()),
        "retained_features": 0,
        "rejected_features": 0,
        "provisional_features": matrix.shape[1],
        "exact_nonconstant_duplicate_groups": [v for v in duplicate.values() if len(v) > 1],
        "bounds_violations": 0,
        "validation_or_holdout_used": False,
        "policy_changed": False,
        "official_metric_change": None,
        "new_notebook_execution": False,
        "supported_stock_products": list(BOUNDED_PRODUCTS),
        "unsupported_stock_products": ["WHEAT", "FERTILIZER"],
        "latency_ms": {
            "median": float(np.median(latencies)),
            "p95": float(np.quantile(latencies, 0.95)),
            "maximum": float(max(latencies)),
        },
        "serialized_state_bytes_maximum": max(state_sizes),
        "serialized_roundtrips_verified": len(state_sizes),
        "groups": groups,
        "products": totals,
        "registry": registry,
        "lineage": {
            "experiment_report_sha256": file_digest(report_path),
            "episode_manifest_sha256": digest(report["artifact_manifest"]),
            "source_experiment_lineage_sha256": digest(report["lineage"]),
            "analysis_code_sha256": file_digest(Path(__file__)),
            "feature_code_sha256": file_digest(
                root / "src/kaggriculture_research/market_history.py"
            ),
            "matrix_sha256": hashlib.sha256(matrix.tobytes()).hexdigest(),
            "feature_columns_sha256": digest(columns),
        },
    }
    write_json(root / "reports/market_history_research.json", result)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"groups", "products", "registry", "exact_nonconstant_duplicate_groups"}
            }
        )
    )


if __name__ == "__main__":
    main()
