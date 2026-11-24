"""Bar chart of overall association scores."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def plot_association_scores(
    records: list[dict[str, Any]],
    path: str | Path,
    top_n: int = 8,
) -> Path:
    """Write a horizontal bar chart with one panel per disease.

    Panels follow the order in which diseases first appear in ``records``.
    Within a panel the highest score is at the top. ``top_n`` limits each panel.
    """
    if not records:
        raise ValueError("No association records to plot.")
    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for record in records:
        disease_id = record["disease_id"]
        if disease_id not in grouped:
            order.append(disease_id)
            grouped[disease_id] = []
        grouped[disease_id].append(record)

    fig, axes = plt.subplots(
        len(order),
        1,
        figsize=(8.4, 1.15 + 1.45 * len(order)),
        squeeze=False,
        constrained_layout=True,
    )
    for ax, disease_id in zip(axes.ravel(), order, strict=True):
        rows = sorted(
            grouped[disease_id],
            key=lambda record: (record["score"], record["gene"]),
        )[-top_n:]
        ax.barh(
            [record["gene"] for record in rows],
            [record["score"] for record in rows],
            color="#1f4e79",
            height=0.72,
        )
        ax.set_xlim(0, 1)
        ax.set_title(f"{rows[-1]['disease']} ({disease_id})", loc="left", fontsize=10)
        ax.grid(axis="x", color="#d0d7de", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(axis="y", labelsize=8)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes.ravel()[-1].set_xlabel("Open Targets overall association score")

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)
    return output
