"""Plotly notebook figures with an equivalent static fallback for GitHub."""

import base64
import io
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from IPython.display import display

COLORS = ["#19735d", "#d28b36", "#477eb5", "#995a77", "#78883c", "#7765ac", "#528f97", "#8a6d52"]


def show_figure(fig: go.Figure) -> None:
    """Render simple bar/line research figures in both interactive and static viewers."""
    fig.update_layout(
        template="plotly_white",
        colorway=COLORS,
        height=460,
        font={"family": "Arial", "size": 14},
        margin={"l": 65, "r": 30, "t": 70, "b": 75},
    )
    fallback, ax = plt.subplots(figsize=(10.5, 4.7), layout="constrained")
    for i, trace in enumerate(fig.data):
        color = COLORS[i % len(COLORS)]
        if trace.type == "bar":
            ax.bar(list(trace.x), list(trace.y), color=color, label=trace.name)
        elif trace.type == "scatter":
            ax.plot(list(trace.x), list(trace.y), color=color, linewidth=2, label=trace.name)
        else:
            raise ValueError(f"Static fallback is not implemented for {trace.type}")
    ax.set_title(fig.layout.title.text, loc="left", fontsize=16, pad=18, fontweight="bold")
    ax.set_xlabel(fig.layout.xaxis.title.text or "")
    ax.set_ylabel(fig.layout.yaxis.title.text or "")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.16)
    ax.set_axisbelow(True)
    if len(fig.data) > 1:
        ax.legend(frameon=False, ncol=min(4, len(fig.data)), fontsize=8)
    if any(t.type == "bar" for t in fig.data):
        ax.tick_params(axis="x", labelrotation=25)
    image = io.BytesIO()
    fallback.savefig(image, format="png", dpi=145, facecolor="white")
    plt.close(fallback)
    display(
        {
            "application/vnd.plotly.v1+json": json.loads(fig.to_json()),
            "image/png": base64.b64encode(image.getvalue()).decode(),
        },
        raw=True,
    )
