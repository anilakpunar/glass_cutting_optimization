"""Plaka yerlesimlerinin matplotlib ile gorsellestirilmesi.

Her plaka icin bir PNG dosyasi uretir: plaka cercevesi, kullanilan
alan (yesil), fire (gri sablonlu), parca etiketleri ve oryantasyon ok
gosterimleri ile sektorel goruntu olusturur.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

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
]


def render_cutting_layouts(
    result: OptimizationResult, output_dir: str | Path
) -> List[Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    for idx, sheet in enumerate(result.sheets, start=1):
        path = out_dir / f"sheet_{idx:02d}_{sheet.stock.sheet_id}.png"
        _render_one(sheet, idx, path, result.kerf.edge_trim_mm)
        files.append(path)
    return files


def _render_one(
    sheet: SheetSolution, idx: int, path: Path, edge_trim_mm: int
) -> None:
    W = sheet.stock.width_mm
    H = sheet.stock.height_mm

    fig, ax = plt.subplots(figsize=(10, 10 * H / W if W else 10))

    # Plaka cercevesi
    ax.add_patch(
        patches.Rectangle(
            (0, 0), W, H,
            linewidth=2.0, edgecolor="black", facecolor="#F4F5F7",
        )
    )

    # Kenar payi (edge trim) bolgesi
    if edge_trim_mm > 0:
        ax.add_patch(
            patches.Rectangle(
                (0, 0), W, edge_trim_mm,
                facecolor="#DFE1E6", alpha=0.6, edgecolor="none",
            )
        )
        ax.add_patch(
            patches.Rectangle(
                (0, H - edge_trim_mm), W, edge_trim_mm,
                facecolor="#DFE1E6", alpha=0.6, edgecolor="none",
            )
        )
        ax.add_patch(
            patches.Rectangle(
                (0, 0), edge_trim_mm, H,
                facecolor="#DFE1E6", alpha=0.6, edgecolor="none",
            )
        )
        ax.add_patch(
            patches.Rectangle(
                (W - edge_trim_mm, 0), edge_trim_mm, H,
                facecolor="#DFE1E6", alpha=0.6, edgecolor="none",
            )
        )

    # Parcalar
    for i, p in enumerate(sheet.placements):
        color = _PART_COLORS[i % len(_PART_COLORS)]
        ax.add_patch(
            patches.Rectangle(
                (p.x_mm, p.y_mm), p.width_mm, p.height_mm,
                linewidth=1.5, edgecolor="black",
                facecolor=color, alpha=0.7,
            )
        )
        cx = p.x_mm + p.width_mm / 2
        cy = p.y_mm + p.height_mm / 2
        label = f"{p.part_id}\n{p.width_mm}x{p.height_mm}"
        if p.orientation.value == "rotated_90":
            label += "\n[90°]"
        ax.annotate(
            label,
            xy=(cx, cy),
            ha="center", va="center",
            fontsize=8, color="black", fontweight="bold",
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

    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
