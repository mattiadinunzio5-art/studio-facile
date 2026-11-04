"""Grafici statici (PNG) per l'esportazione, con matplotlib in modalità headless."""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Stessi slot categoriali dell'interfaccia (validati CVD), su sfondo chiaro per la stampa usiamo i passi "light".
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def line_chart(title: str, x: list, series: dict[str, list], ylabel: str = "", source: str = "") -> bytes:
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=150)
    for i, (name, ys) in enumerate(series.items()):
        ax.plot(x, [float("nan") if v is None else v for v in ys], label=name, color=COLORS[i % len(COLORS)], linewidth=1.6)
    ax.set_title(title, fontsize=10, loc="left")
    ax.set_ylabel(ylabel, fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if len(series) > 1:
        ax.legend(fontsize=7, frameon=False)
    n = len(x)
    if n > 12:
        step = max(1, n // 8)
        ax.set_xticks(range(0, n, step))
        ax.set_xticklabels([x[i] for i in range(0, n, step)], rotation=0)
    if source:
        fig.text(0.01, 0.01, f"Fonte: {source}", fontsize=6, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def font_path() -> str:
    """DejaVu Sans incluso in matplotlib: copre i caratteri accentati e i simboli usati nei rapporti."""
    import os

    return os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf")


def font_bold_path() -> str:
    import os

    return os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans-Bold.ttf")
