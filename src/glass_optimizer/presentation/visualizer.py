"""Plaka yerlesimlerinin matplotlib ile gorsellestirilmesi.

Her plaka icin bir figur uretir: plaka cercevesi, kenar payi, parcalar
(ayni olcudeki parcalar ayni renkte - homojenlik gorunur) ve etiketler.
`render_cutting_layouts` bunu PNG'ye yazar; `build_sheet_figure` ise
figuru dondurur (orn. Streamlit arayuzu icin).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ..domain.models import OptimizationResult, SheetSolution


_PART_COLORS = [
    "#4C9AFF",
    "#36B37E",
    "#FFAB00",
    "#FF5630",
    "#6554C0",
    "#00B8D9",
    "#FF8B00",
    "#8777D9",
    "#57D9A3",
    "#FFC400",
]


def _base_id(part_id: str) -> str:
    return part_id.split("#")[0]


def render_cutting_layouts(
    result: OptimizationResult, output_dir: str | Path
) -> List[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    for idx, sheet in enumerate(result.sheets, start=1):
        path = out_dir / f"sheet_{idx:02d}_{sheet.stock.sheet_id}.png"
        fig = build_sheet_figure(sheet, idx, result.kerf.edge_trim_mm)
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        files.append(path)
    return files


def build_sheet_figure(
    sheet: SheetSolution, idx: int, edge_trim_mm: int
) -> Figure:
    """Tek plakanin matplotlib figurunu uretir ve dondurur."""
    W = sheet.stock.width_mm
    H = sheet.stock.height_mm

    fig, ax = plt.subplots(figsize=(10, 10 * H / W if W else 10))

    ax.add_patch(
        patches.Rectangle(
            (0, 0), W, H,
            linewidth=2.0, edgecolor="black", facecolor="#F4F5F7",
        )
    )

    if edge_trim_mm > 0:
        for rect in (
            (0, 0, W, edge_trim_mm),
            (0, H - edge_trim_mm, W, edge_trim_mm),
            (0, 0, edge_trim_mm, H),
            (W - edge_trim_mm, 0, edge_trim_mm, H),
        ):
            ax.add_patch(
                patches.Rectangle(
                    (rect[0], rect[1]), rect[2], rect[3],
                    facecolor="#DFE1E6", alpha=0.6, edgecolor="none",
                )
            )

    # Ayni olcudeki (ayni base id) parcalar ayni renkte
    color_map: Dict[str, str] = {}
    for p in sheet.placements:
        base = _base_id(p.part_id)
        if base not in color_map:
            color_map[base] = _PART_COLORS[len(color_map) % len(_PART_COLORS)]
        ax.add_patch(
            patches.Rectangle(
                (p.x_mm, p.y_mm), p.width_mm, p.height_mm,
                linewidth=1.2, edgecolor="black",
                facecolor=color_map[base], alpha=0.78,
            )
        )
        label = f"{base}\n{p.width_mm}x{p.height_mm}"
        if p.orientation.value == "rotated_90":
            label += "\n[90°]"
        ax.annotate(
            label,
            xy=(p.x_mm + p.width_mm / 2, p.y_mm + p.height_mm / 2),
            ha="center", va="center",
            fontsize=7, color="black", fontweight="bold",
        )

    util = sheet.utilization * 100
    ax.set_title(
        f"Plaka #{idx} - {sheet.stock.sheet_id}  "
        f"({W}x{H} mm) - Kullanim: %{util:.1f}",
        fontsize=12,
    )
    ax.set_xlim(-W * 0.02, W * 1.02)
    ax.set_ylim(-H * 0.02, H * 1.02)
    ax.set_aspect("equal")
    ax.set_xlabel("Genislik (mm)")
    ax.set_ylabel("Yukseklik (mm)")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()
    return fig
