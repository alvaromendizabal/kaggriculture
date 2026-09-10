"""Post-hoc held-stock diagnostics; opponent-private observations are evaluator-only.

No policy or feature consumes this analysis. It does not fit, tune or select an agent.
"""

import copy
import gzip
import json
from pathlib import Path

import pandas as pd

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, write_json
from kaggriculture_research.environment import game


def post_farm(record):
    obs = record["observation"]
    farm = copy.deepcopy(obs["farms"][obs["player"]])
    private = copy.deepcopy(obs["private"])
    for index, action in enumerate([record["action"]["farmer"], *record["action"]["hands"]]):
        game._apply_unit_action(farm, private, index, action, 10, obs["day"], 24, 100)
    return private


def main():
    root = Path(__file__).resolve().parents[1]
    report = json.loads((root / "reports/market_research.json").read_text())
    rows = []
    for artifact in report["artifact_manifest"]:
        path = root / artifact["path"]
        if file_digest(path) != artifact["sha256"]:
            raise ValueError("Trace differs from recorded experiment")
        with gzip.open(path, "rt") as stream:
            summary = json.load(stream)["payload"]["summary"]
        if summary["arm"][1] != "1":
            continue
        lineage = {**report["lineage"], **{k: summary[k] for k in ("seed", "seat", "arm")}}
        payload = load_checkpoint(path, lineage)
        if payload is None:
            raise ValueError("Trace lineage differs")
        records = {(r["player"], r["observation"]["step"]): r for r in payload["records"]}
        seat = summary["seat"]
        for step in range(719):
            record = records[seat, step]
            if record["diagnostics"]["interventions"]["market_timing"] == 0:
                continue
            if step == 718:
                raise ValueError("Market timing held stock at the final sale callback")
            own_stock = post_farm(record)["shed"]
            ours = {o[1]: o[2] for o in record["action"]["market"] if o[0] == "SELL"}
            rival_record = records[1 - seat, step]
            rival_stock = post_farm(rival_record)["shed"]
            rival_sales = {}
            for order in rival_record["action"]["market"]:
                if order[0] == "SELL":
                    _, item, quantity = order
                    rival_sales[item] = rival_sales.get(item, 0) + quantity
            if len(rival_record["action"]["market"]) > 10:
                raise ValueError("Opponent exceeded market-order scope")
            if any(q > rival_stock.get(item, 0) for item, q in rival_sales.items()):
                raise ValueError("Opponent sale was not executable from its own stock")
            for item in game.PRODUCTS:
                held = own_stock.get(item, 0) - ours.get(item, 0)
                if held <= 0:
                    continue
                obs = record["observation"]
                next_obs = records[seat, step + 1]["observation"]
                before = game.market_price(item, obs["market"]["inventory"][item])
                after = game.market_price(item, next_obs["market"]["inventory"][item])
                rows.append(
                    {
                        "seed": summary["seed"],
                        "seat": seat,
                        "arm": summary["arm"],
                        "step": step,
                        "product": item,
                        "held_units": held,
                        "same_turn_rival_sale_units": rival_sales.get(item, 0),
                        "quote_before": before,
                        "quote_next_callback": after,
                        "quote_change": after - before,
                    }
                )
    frame = pd.DataFrame(rows)
    path = root / "reports/market_hold_diagnostics.csv"
    frame.to_csv(path, index=False)
    groups = []
    for arm, group in frame.groupby("arm"):
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
    write_json(
        root / "reports/market_hold_analysis.json",
        {
            "scope": (
                "Post-hoc observational mechanism diagnostic; "
                "not a causal mediation estimate or policy input"
            ),
            "groups": groups,
            "analysis_code_sha256": file_digest(Path(__file__)),
            "diagnostics_csv_sha256": file_digest(path),
            "experiment_report_sha256": file_digest(root / "reports/market_research.json"),
            "episode_manifest_sha256": digest(report["artifact_manifest"]),
            "validation_or_holdout_used": False,
        },
    )
    print(json.dumps(groups))


if __name__ == "__main__":
    main()
