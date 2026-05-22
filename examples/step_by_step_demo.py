"""Adim adim MaxRects gosterimi - dokuman gorsellerini uretir.

Uretim cozucusunun (`MaxRectsSheetSolver`) bos-dikdortgen bolme ve
prune mantigini BIREBIR kullanir; her parca yerlesiminden sonraki
durumu PNG olarak `docs/images/` altina yazar.

    python examples/step_by_step_demo.py
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from glass_optimizer.domain.enums import CutOrientation
from glass_optimizer.domain.models import KerfSettings, PartOrder, Placement, StockSheet
from glass_optimizer.optimization.cpsat_solver import _expand
from glass_optimizer.optimization.maxrects_solver import _FreeRect, MaxRectsSheetSolver

# ---- Basit ornek ----------------------------------------------------------
SHEET = StockSheet(sheet_id="DEMO", width_mm=1200, height_mm=800)
PARTS = [
    PartOrder(part_id="A", width_mm=600, height_mm=400, quantity=1, priority=5),
    PartOrder(part_id="B", width_mm=500, height_mm=300, quantity=1, priority=5),
    PartOrder(part_id="C", width_mm=400, height_mm=400, quantity=1, priority=5),
    PartOrder(part_id="D", width_mm=300, height_mm=180, quantity=2, priority=5),
]
KERF = KerfSettings(kerf_mm=0, edge_trim_mm=0, min_offcut_mm=100)

_COLORS = ["#4C9AFF", "#36B37E", "#FFAB00", "#FF5630", "#6554C0", "#00B8D9"]


def _draw(
    placements: List[Placement],
    free_rects: List[_FreeRect],
    highlight: Placement | None,
    title: str,
    path: Path,
) -> None:
    W, H = SHEET.width_mm, SHEET.height_mm
    fig, ax = plt.subplots(figsize=(8, 8 * H / W))

    ax.add_patch(
        patches.Rectangle((0, 0), W, H, lw=2, edgecolor="black", facecolor="#F4F5F7")
    )

    # Yerlesen parcalar
    for i, p in enumerate(placements):
        is_new = highlight is not None and p is highlight
        ax.add_patch(
            patches.Rectangle(
                (p.x_mm, p.y_mm), p.width_mm, p.height_mm,
                lw=2.5 if is_new else 1.2,
                edgecolor="#091E42" if is_new else "black",
                facecolor=_COLORS[i % len(_COLORS)],
                alpha=0.85 if is_new else 0.55,
            )
        )
        ax.annotate(
            p.part_id.split("#")[0],
            xy=(p.x_mm + p.width_mm / 2, p.y_mm + p.height_mm / 2),
            ha="center", va="center", fontsize=13, fontweight="bold",
        )

    # Bos dikdortgenler (kesikli kirmizi)
    for j, r in enumerate(free_rects):
        ax.add_patch(
            patches.Rectangle(
                (r.x, r.y), r.w, r.h,
                lw=1.5, edgecolor="#DE350B", facecolor="#DE350B",
                alpha=0.06, linestyle="--",
            )
        )
        ax.annotate(
            f"F{j + 1}\n{r.w}x{r.h}",
            xy=(r.x + r.w / 2, r.y + r.h / 2),
            ha="center", va="center", fontsize=8, color="#DE350B",
        )

    ax.set_title(title, fontsize=12)
    ax.set_xlim(-W * 0.03, W * 1.03)
    ax.set_ylim(-H * 0.03, H * 1.03)
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "docs" / "images"
    out.mkdir(parents=True, exist_ok=True)

    expanded = _expand(PARTS)
    expanded.sort(
        key=lambda e: (-e.base.priority, -(e.base.width_mm * e.base.height_mm))
    )

    free_rects: List[_FreeRect] = [_FreeRect(0, 0, SHEET.width_mm, SHEET.height_mm)]
    placements: List[Placement] = []

    # Adim 0: bos plaka
    _draw(placements, free_rects, None, "Adim 0: Bos plaka - tek bos dikdortgen (F1)",
          out / "step_0.png")

    step = 1
    for ep in expanded:
        p = ep.base
        best = MaxRectsSheetSolver._find_best_fit(
            free_rects, p.width_mm + KERF.kerf_mm, p.height_mm + KERF.kerf_mm,
            p.allow_rotation,
        )
        if best is None:
            continue
        x, y, used_w, used_h, rotated = best

        new_placement = Placement(
            part_id=ep.instance_id, x_mm=x, y_mm=y,
            width_mm=used_w - KERF.kerf_mm, height_mm=used_h - KERF.kerf_mm,
            orientation=CutOrientation.ROTATED_90 if rotated else CutOrientation.NORMAL,
        )
        placements.append(new_placement)

        MaxRectsSheetSolver._split_overlapping(free_rects, x, y, used_w, used_h)
        MaxRectsSheetSolver._prune_contained(free_rects)

        _draw(
            placements, free_rects, new_placement,
            f"Adim {step}: '{p.part_id}' ({p.width_mm}x{p.height_mm}) yerlesti "
            f"-> {len(free_rects)} bos dikdortgen",
            out / f"step_{step}.png",
        )
        step += 1

    print(f"{step} adim gorseli uretildi: {out}")


if __name__ == "__main__":
    main()
