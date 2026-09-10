"""Matched interactive and static terminal-study figures with explicit metric scope."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from IPython.display import Image, display

ARMS = ["baseline", "feed", "joint"]
COLORS = ["#64748b", "#2563eb", "#0f766e"]


def show_scores(games) -> None:
    scores = games.pivot_table(index="arm", columns="opponent", values="match_score").reindex(ARMS)
    figure = go.Figure()
    static, axis = plt.subplots(figsize=(9, 4.5), layout="constrained")
    positions = np.arange(3)
    for i, opponent in enumerate(scores.columns):
        values = scores[opponent].tolist()
        figure.add_bar(
            name=opponent,
            x=ARMS,
            y=values,
            marker_color=COLORS[i + 1],
            text=[f"{v:.3f}" for v in values],
            textposition="outside",
            cliponaxis=False,
        )
        bars = axis.bar(
            positions + (i - 0.5) * 0.34, values, 0.34, label=opponent, color=COLORS[i + 1]
        )
        axis.bar_label(bars, fmt="%.3f", padding=4)
    title = "Final-day interventions · local match score"
    figure.update_layout(
        title=title,
        template="plotly_white",
        yaxis_range=[0, 1],
        yaxis_title="Win + half a tie",
        xaxis_title="Sequential intervention",
        barmode="group",
        margin={"t": 90, "b": 60, "l": 60, "r": 20},
    )
    axis.set(xticks=positions, xticklabels=ARMS, ylim=(0, 1), ylabel="Win + half a tie")
    axis.set_title(title, pad=25)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2, frameon=False)
    axis.spines[["right", "top"]].set_visible(False)
    buffer = BytesIO()
    static.savefig(buffer, format="png", dpi=150)
    plt.close(static)
    display({"application/vnd.plotly.v1+json": figure.to_plotly_json()}, raw=True)
    display(Image(data=buffer.getvalue()))


def show_coin_effects(effects) -> None:
    rows = effects[(effects.opponent == "pooled") & (effects.metric == "coins")]
    values = rows.effect.to_numpy()
    low = values - rows.bootstrap_low.to_numpy()
    high = rows.bootstrap_high.to_numpy() - values
    labels = rows.contrast.tolist()
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=COLORS,
            error_x={"type": "data", "symmetric": False, "array": high, "arrayminus": low},
        )
    )
    title = "Own-coin differences · descriptive seed-cluster intervals"
    figure.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Paired coin difference",
        yaxis={"autorange": "reversed"},
    )
    static, axis = plt.subplots(figsize=(9, 4.5), layout="constrained")
    axis.barh(labels, values, xerr=np.vstack([low, high]), color=COLORS, capsize=5)
    axis.invert_yaxis()
    axis.axvline(0, color="#334155", linewidth=0.8)
    axis.set_xlabel("Paired coin difference · four development seed clusters")
    axis.set_title(title, pad=18)
    axis.grid(axis="x", alpha=0.18)
    axis.set_axisbelow(True)
    axis.spines[["right", "top"]].set_visible(False)
    buffer = BytesIO()
    static.savefig(buffer, format="png", dpi=150)
    plt.close(static)
    display({"application/vnd.plotly.v1+json": figure.to_plotly_json()}, raw=True)
    display(Image(data=buffer.getvalue()))
