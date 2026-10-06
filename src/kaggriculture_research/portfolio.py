"""Small aggregate-evidence helpers; no engine, private model, or cloud access."""

from __future__ import annotations

from collections.abc import Mapping
from math import isclose, isfinite


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label)
    value = float(value)
    _require(isfinite(value), label)
    return value


def evidence_summary(report: Mapping[str, object]) -> dict[str, object]:
    """Validate the arithmetic used in the review, without claiming raw-game verification."""
    snapshot = report["latest_snapshot"]
    alignment = report["validation_alignment"]
    ledger = report["project_ledger"]
    development = report["milestones"]["ladder_alignment"]["development"]
    _require(snapshot["observed_utc"] == "2026-09-30T02:31:37Z", "SNAPSHOT_DATE")
    for key in (
        "attempts",
        "successful_intended_runs",
        "execution_failures",
        "authorization_stops",
        "other_controlled_stops",
    ):
        value = ledger[key]
        _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, key)
    counts = {
        "Successful executions": ledger["successful_intended_runs"],
        "Execution failures": ledger["execution_failures"],
        "Controlled stops": ledger["authorization_stops"] + ledger["other_controlled_stops"],
    }
    _require(sum(counts.values()) == ledger["attempts"], "ATTEMPT_TOTAL")
    for prefix in ("recent_keeper", "development"):
        count = alignment[f"{prefix}_episodes"]
        wins = alignment[f"{prefix}_wins"]
        ties = alignment[f"{prefix}_ties"]
        losses = alignment[f"{prefix}_losses"]
        for value in (count, wins, ties, losses):
            _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, prefix)
        _require(count > 0 and wins + ties + losses == count, f"{prefix}_COUNT")
        rate = _number(alignment[f"{prefix}_score_rate"], f"{prefix}_RATE")
        _require(isclose((wins + ties / 2) / count, rate, abs_tol=1e-9), f"{prefix}_RATE")
    labels = {
        "Keeper": "keeper",
        "Labor": "labor",
        "Timing": "timing_current",
        "Shop router": "shop_router_v7",
        "Smarter feed": "v38_smarter_feed",
    }
    rates = {label: _number(development[key]["score_rate"], key) for label, key in labels.items()}
    _require(all(0 <= value <= 1 for value in rates.values()), "SCORE_RANGE")
    _require(
        isclose(rates["Keeper"], alignment["development_score_rate"], abs_tol=1e-9),
        "DEVELOPMENT_KEEPER_RATE",
    )
    keeper_rating = _number(snapshot["keeper_rating"], "KEEPER_RATING")
    returned_rating = _number(snapshot["highest_returned_leaderboard_score"], "RETURNED_RATING")
    gap = _number(snapshot["gap_to_highest_returned"], "RATING_GAP")
    _require(isclose(returned_rating - keeper_rating, gap, abs_tol=1e-9), "RATING_GAP")
    return {
        "observed_utc": snapshot["observed_utc"],
        "development_score_rates": rates,
        "execution_counts": counts,
        "attempts": ledger["attempts"],
        "recent_keeper_score_rate": alignment["recent_keeper_score_rate"],
        "keeper_rating": keeper_rating,
        "highest_returned_rating": returned_rating,
        "gap_to_highest_returned": gap,
    }


def chart_bundle(summary: Mapping[str, object], kind: str) -> dict[str, object]:
    """Render the same aggregate values through Plotly and a static Matplotlib SVG."""
    import io
    import json

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go

    if kind == "development":
        values = summary["development_score_rates"]
        title = "Fixed policies on 24 older ladder episodes"
        x_title = "Win/tie score rate"
        colors = ["#247B7B"] + ["#9BB8C3"] * (len(values) - 1)
    elif kind == "ledger":
        values = summary["execution_counts"]
        title = "Historical execution ledger: 75 attempts"
        x_title = "Top-level attempts"
        colors = ["#247B7B", "#BC6252", "#C7A85E"]
    else:
        raise ValueError("UNKNOWN_CHART_KIND")
    labels, numbers = list(values), list(values.values())
    figure = go.Figure(
        go.Bar(x=numbers, y=labels, orientation="h", marker_color=colors, name="Recorded aggregate")
    )
    figure.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis={"autorange": "reversed"},
        template="plotly_white",
        width=900,
        height=360,
        margin={"l": 165, "r": 35, "t": 65, "b": 65},
        meta={"evidence_cutoff": summary["observed_utc"], "scope": "aggregate summary"},
    )
    if kind == "development":
        figure.update_xaxes(tickformat=".0%", range=[0, 0.55])
    with plt.rc_context({"svg.hashsalt": "kaggriculture-portfolio", "font.size": 11}):
        static, axis = plt.subplots(figsize=(9, 3.6))
        axis.barh(labels, numbers, color=colors)
        axis.invert_yaxis()
        axis.set_title(title, loc="left", pad=14)
        axis.set_xlabel(x_title)
        axis.spines[["top", "right"]].set_visible(False)
        axis.set_axisbelow(True)
        axis.grid(axis="x", alpha=0.2)
        for position, value in enumerate(numbers):
            label = f"{value:.1%}" if kind == "development" else str(value)
            axis.text(value, position, f"  {label}", va="center", fontsize=10)
        axis.set_xlim(0, 0.55 if kind == "development" else max(numbers) * 1.2)
        if kind == "development":
            from matplotlib.ticker import PercentFormatter

            axis.xaxis.set_major_formatter(PercentFormatter(1))
        static.tight_layout()
        buffer = io.StringIO()
        static.savefig(buffer, format="svg", metadata={"Date": None})
        plt.close(static)
    return {
        "application/vnd.plotly.v1+json": json.loads(figure.to_json()),
        "image/svg+xml": buffer.getvalue(),
    }
