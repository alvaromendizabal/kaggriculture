"""Audit tighter public-cash bounds on the original 48 verified development games."""

import gzip
import json
from collections import defaultdict
from itertools import product
from pathlib import Path

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.cash_history import CashHistory
from kaggriculture_research.environment import engine_manifest
from kaggriculture_research.market_experiment import episode_hash
from kaggriculture_research.market_history import (
    BOUNDED_PRODUCTS,
    MarketHistory,
    own_nonbuyable_sales,
)
from kaggriculture_research.progress import Progress


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = json.loads((root / "reports/market_research.json").read_text())
    if engine_manifest() != source["lineage"]["engine"]:
        raise ValueError("Source interpreter changed")
    for name, sha in source["lineage"]["code"].items():
        if file_digest(root / "src/kaggriculture_research" / name) != sha:
            raise ValueError(f"Frozen source changed: {name}")
    protocol = source["lineage"]["protocol"]
    expected = set(product(protocol["development_seeds"], protocol["seats"], protocol["arms"]))
    seen = set()
    groups = []
    progress = Progress()
    with progress.stage("cash_supply_development_replay"):
        for artifact in source["artifact_manifest"]:
            path = root / artifact["path"]
            if file_digest(path) != artifact["sha256"]:
                raise ValueError("Source episode checksum differs")
            with gzip.open(path, "rt") as stream:
                summary = json.load(stream)["payload"]["summary"]
            lineage = {**source["lineage"], **{k: summary[k] for k in ("seed", "seat", "arm")}}
            payload = load_checkpoint(path, lineage)
            if payload is None or episode_hash(payload) != artifact["semantic_sha256"]:
                raise ValueError("Source semantic identity differs")
            key = tuple(summary[k] for k in ("seed", "seat", "arm"))
            if key not in expected or key in seen:
                raise ValueError("Duplicated or unregistered source episode")
            seen.add(key)
            seat = summary["seat"]
            records = {(r["player"], r["observation"]["step"]): r for r in payload["records"]}
            loose, tight = MarketHistory(), CashHistory()
            metrics = {p: defaultdict(int) for p in BOUNDED_PRODUCTS}
            sales = None
            for step in range(719):
                record = records[seat, step]
                loose.observe(record["observation"])
                features = tight.observe(record["observation"])
                if len(features.values) != 42:
                    raise ValueError("Cash feature schema differs")
                loose.record_action(record["action"])
                tight.record_action(record["action"])
                if step % 24 == 0 or step == 718:
                    tight = CashHistory.from_json(tight.to_json())
                # Evaluator-only truth: never passed to either history extractor.
                rival = records[1 - seat, step]
                private = rival["observation"]["private"]
                for item, row in metrics.items():
                    actual = private["shed"].get(item, 0) + sum(
                        i.get(item, 0) for i in private["inventories"]
                    )
                    if not actual <= tight.upper[item] <= loose.upper[item]:
                        raise ValueError(
                            f"Stock-bound containment failed: {summary}, {step}, {item}"
                        )
                    row["callbacks"] += 1
                    row["stock_positive"] += int(actual > 0)
                    row["loose_excess"] += loose.upper[item] - actual
                    row["cash_excess"] += tight.upper[item] - actual
                    row["loose_false_positive"] += int(actual == 0 and loose.upper[item] > 0)
                    row["cash_false_positive"] += int(actual == 0 and tight.upper[item] > 0)
                    row["strictly_tighter"] += int(tight.upper[item] < loose.upper[item])
                    if step:
                        interval = tight.base.rows[-1][item]
                        if not interval["sales_lower"] <= sales[item] <= interval["sales_upper"]:
                            raise ValueError("Cash sale bounds exclude actual rival sales")
                        row["sale_units"] += sales[item]
                        row["cash_sale_lower"] += int(interval["sales_lower"])
                        row["loose_sale_lower"] += int(loose.rows[-1][item]["sales_lower"])
                sales = own_nonbuyable_sales(rival["observation"], rival["action"])
            groups.extend(
                {**{k: summary[k] for k in ("seed", "seat", "arm")}, "product": item, **dict(row)}
                for item, row in metrics.items()
            )
    if seen != expected or len(seen) != 48:
        raise ValueError("Source replay grid is incomplete")
    products = []
    for item in BOUNDED_PRODUCTS:
        subset = [g for g in groups if g["product"] == item]
        fields = set(subset[0]) - {"seed", "seat", "arm", "product"}
        products.append({"product": item, **{k: sum(g[k] for g in subset) for k in sorted(fields)}})
    result = {
        "scope": "Post-hoc development identification audit; not a policy evaluation",
        "games_reused": len(groups) // len(BOUNDED_PRODUCTS),
        "new_games": 0,
        "callback_vectors": 48 * 719,
        "candidate_features": 42,
        "bound_violations": 0,
        "validation_or_holdout_used": False,
        "products": products,
        "groups": groups,
        "lineage": {
            "source_report_sha256": file_digest(root / "reports/market_research.json"),
            "episode_manifest_sha256": digest(source["artifact_manifest"]),
            "feature_code_sha256": file_digest(root / "src/kaggriculture_research/cash_history.py"),
            "analysis_code_sha256": file_digest(Path(__file__)),
        },
    }
    write_json(root / "reports/cash_history_research.json", result)
    print(json.dumps(products))


if __name__ == "__main__":
    main()
