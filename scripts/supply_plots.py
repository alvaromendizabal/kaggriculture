"""Matched Plotly/static score views with an explicit, identical 0–1 scale."""

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from IPython.display import Image, display


def show_match_scores(scores) -> None:
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
        )
        bars = axis.bar(
            positions + (index - 0.5) * width, values, width, label=opponent, color=colors[index]
        )
        axis.bar_label(bars, fmt="%.3f", padding=3, fontsize=9)
    title = "Rival-supply information · local match score"
    interactive.update_layout(
        title=title,
        template="plotly_white",
        barmode="group",
        xaxis_title="Fixed information arm",
        yaxis_title="Win + half a tie",
        yaxis_range=[0, 1],
        legend_title="Frozen opponent",
    )
    axis.set(
        xticks=positions,
        xticklabels=labels,
        ylim=(0, 1),
        xlabel="Fixed information arm",
        ylabel="Win + half a tie",
        title=title,
    )
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
