"""Matched Plotly/static score views with an explicit, identical 0–1 scale."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from IPython.display import Image, display


def show_livestock_scores(scores) -> None:
    labels = [str(x) for x in scores.index]
    colors = ["#2563eb", "#0f766e"]
    interactive = go.Figure()
    static, axis = plt.subplots(figsize=(9, 4.7), layout="constrained")
    positions = np.arange(len(labels))
    width = 0.34
    for index, opponent in enumerate(scores.columns):
        values = scores[opponent].tolist()
        interactive.add_bar(
            name=opponent,
            x=labels,
            y=values,
            marker_color=colors[index],
            text=[f"{v:.3f}" for v in values],
            textposition="outside",
            cliponaxis=False,
        )
        bars = axis.bar(
            positions + (index - 0.5) * width, values, width, label=opponent, color=colors[index]
        )
        axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
    title = "Livestock resource loops · local match score"
    interactive.update_layout(
        title=title,
        template="plotly_white",
        barmode="group",
        xaxis_title="Sequential component arm",
        yaxis_title="Win + half a tie",
        yaxis_range=[0, 1],
        legend_title="Frozen opponent",
        margin={"t": 90, "b": 70, "l": 65, "r": 25},
    )
    axis.set(
        xticks=positions,
        xticklabels=labels,
        ylim=(0, 1),
        xlabel="Sequential component arm",
        ylabel="Win + half a tie",
    )
    axis.set_title(title, pad=28)
    axis.set_yticks(np.linspace(0, 1, 5))
    axis.grid(axis="y", alpha=0.18)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
    buffer = BytesIO()
    static.savefig(buffer, format="png", dpi=150)
    plt.close(static)
    display({"application/vnd.plotly.v1+json": interactive.to_plotly_json()}, raw=True)
    display(Image(data=buffer.getvalue()))


def show_resource_work(games) -> None:
    from plotly.subplots import make_subplots

    columns = ["fed_units", "commands_CARE", "applied_units"]
    titles = ["Wheat consumed as feed", "Successful CARE actions", "Fertilizer applications"]
    arms = ["routine", "feed", "care", "fertilizer"]
    means = games.groupby("arm")[columns].mean().reindex(arms)
    interactive = make_subplots(rows=1, cols=3, subplot_titles=titles)
    static, axes = plt.subplots(1, 3, figsize=(12, 4.5), layout="constrained")
    colors = ["#94a3b8", "#2563eb", "#0f766e", "#a16207"]
    for index, (metric, title) in enumerate(zip(columns, titles, strict=True)):
        values = means[metric].tolist()
        interactive.add_bar(
            x=arms, y=values, marker_color=colors, showlegend=False, row=1, col=index + 1
        )
        bars = axes[index].bar(arms, values, color=colors)
        axes[index].bar_label(bars, fmt="%.1f", fontsize=8, padding=3)
        axes[index].set_title(title, pad=18)
        axes[index].set_ylim(0, max(values) * 1.2 + 1)
        axes[index].tick_params(axis="x", rotation=25)
        axes[index].grid(axis="y", alpha=0.15)
        axes[index].set_axisbelow(True)
        axes[index].spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Mean events or units per game")
    interactive.update_layout(title="Resource use · 16 games per arm", template="plotly_white")
    interactive.update_yaxes(rangemode="tozero")
    buffer = BytesIO()
    static.savefig(buffer, format="png", dpi=150)
    plt.close(static)
    display({"application/vnd.plotly.v1+json": interactive.to_plotly_json()}, raw=True)
    display(Image(data=buffer.getvalue()))
