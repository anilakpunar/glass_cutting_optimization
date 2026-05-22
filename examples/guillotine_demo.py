"""Adim adim GUILLOTINE gosterimi - dokuman gorsellerini uretir.

Uretim cozucusunun (`GuillotineSheetSolver`) blok-secme mantigini
(`_best_block`, `_fit_grid`) BIREBIR kullanir; recursive guillotine
paketlemenin her blok adimini ve guillotine kesim cizgilerini PNG
olarak `docs/images/` altina yazar.

    python examples/guillotine_demo.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from glass_optimizer.domain.enums import CutOrientation
from glass_optimizer.domain.models import KerfSettings, PartOrder, Placement, StockSheet
from glass_optimizer.optimization.guillotine_solver import GuillotineSheetSolver, _Rect

# ---- Basit ornek ----------------------------------------------------------
SHEET = StockSheet(sheet_id="DEMO", width_mm=1200, height_mm=950)
PARTS = [
    PartOrder(part_id="A", width_mm=400, height_mm=360, quantity=4, priority=5, allow_rotation=False),
    PartOrder(part_id="B", width_mm=360, height_mm=240, quantity=4, priority=5, allow_rotation=False),
    PartOrder(part_id="C", width_mm=230, height_mm=200, quantity=6, priority=5, allow_rotation=False),
]
KERF = KerfSettings(kerf_mm=0, edge_trim_mm=0, min_offcut_mm=100)

_PART_COLOR = {"A": "#4C9AFF", "B": "#36B37E", "C": "#FFAB00"}


def _draw(
    placements: List[Placement],
    pending: List[_Rect],
    current: _Rect | None,
    cut_lines: List[Tuple[int, int, int, int]],
    title: str,
    path: Path,
) -> None:
    W, H = SHEET.width_mm, SHEET.height_mm
    fig, ax = plt.subplots(figsize=(8, 8 * H / W))
    ax.add_patch(
        patches.Rectangle((0, 0), W, H, lw=2, edgecolor="black", facecolor="#F4F5F7")
    )

    # Bekleyen (henuz islenmemis) bos dikdortgenler
    for r in pending:
        ax.add_patch(
            patches.Rectangle(
                (r.x, r.y), r.w, r.h, lw=1.2, edgecolor="#8993A4",
                facecolor="#8993A4", alpha=0.10, linestyle=":",
            )
        )

    # Yerlesen parcalar - part tipine gore renk (homojenlik gorunur)
    for p in placements:
        base = p.part_id.split("#")[0]
        ax.add_patch(
            patches.Rectangle(
                (p.x_mm, p.y_mm), p.width_mm, p.height_mm,
                lw=1.2, edgecolor="black",
                facecolor=_PART_COLOR.get(base, "#6554C0"), alpha=0.75,
            )
        )
        ax.annotate(
            base, xy=(p.x_mm + p.width_mm / 2, p.y_mm + p.height_mm / 2),
            ha="center", va="center", fontsize=11, fontweight="bold",
        )

    # Su an islenen dikdortgen
    if current is not None:
        ax.add_patch(
            patches.Rectangle(
                (current.x, current.y), current.w, current.h,
                lw=2.5, edgecolor="#DE350B", facecolor="none",
            )
        )

    # Guillotine kesim cizgileri (kalin kirmizi)
    for (x1, y1, x2, y2) in cut_lines:
        ax.plot([x1, x2], [y1, y2], color="#DE350B", lw=2.0, linestyle="--")

    ax.set_title(title, fontsize=11)
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

    solver = GuillotineSheetSolver.__new__(GuillotineSheetSolver)  # helper'lar icin
    solver.settings = None  # type: ignore

    pool: Dict[str, int] = {p.part_id: p.quantity for p in PARTS}
    used: Dict[str, int] = {p.part_id: 0 for p in PARTS}
    placements: List[Placement] = []

    root = _Rect(0, 0, SHEET.width_mm, SHEET.height_mm)
    work: List[_Rect] = [root]

    _draw(placements, work, None, [],
          "Guillotine Adim 0: Bos plaka", out / "g_step_0.png")

    step = 1
    k = KERF.kerf_mm
    # Recursive paketlemeyi yiginla (stack) replikle - uretim _pack ile ayni mantik
    while work:
        # Buyuk artigi once isle (uretimdeki gibi)
        work.sort(key=lambda r: r.area, reverse=True)
        rect = work.pop(0)
        block = solver._best_block(rect, PARTS, pool, KERF)
        if block is None:
            continue
        part, pw, ph, rotated, gc, gr = block

        cut_lines: List[Tuple[int, int, int, int]] = []
        for r in range(gr):
            for c in range(gc):
                if pool[part.part_id] <= 0:
                    break
                px = rect.x + c * (pw + k)
                py = rect.y + r * (ph + k)
                used[part.part_id] += 1
                placements.append(Placement(
                    part_id=f"{part.part_id}#{used[part.part_id]}",
                    x_mm=px, y_mm=py, width_mm=pw, height_mm=ph,
                    orientation=CutOrientation.ROTATED_90 if rotated else CutOrientation.NORMAL,
                ))
                pool[part.part_id] -= 1

        block_w = gc * pw + (gc - 1) * k
        block_h = gr * ph + (gr - 1) * k

        # Guillotine kesim cizgileri: blok sagi (dikey) ve blok ustu (yatay)
        if rect.x + block_w < rect.x + rect.w:
            cut_lines.append((rect.x + block_w, rect.y, rect.x + block_w, rect.y + rect.h))
        if rect.y + block_h < rect.y + rect.h:
            cut_lines.append((rect.x, rect.y + block_h, rect.x + rect.w, rect.y + block_h))

        # Artiklar - uretim _pack ile ayni A/B guillotine bolme secimi
        top_h = rect.h - block_h - k
        right_w = rect.w - block_w - k
        topA = _Rect(rect.x, rect.y + block_h + k, rect.w, top_h)
        rightA = _Rect(rect.x + block_w + k, rect.y, right_w, block_h)
        topB = _Rect(rect.x, rect.y + block_h + k, block_w, top_h)
        rightB = _Rect(rect.x + block_w + k, rect.y, right_w, rect.h)
        ea = lambda r: r.area if (r.w >= 1 and r.h >= 1) else 0
        if max(ea(topA), ea(rightA)) >= max(ea(topB), ea(rightB)):
            top, right = topA, rightA
        else:
            top, right = topB, rightB
        for rr in (top, right):
            if rr.w >= 1 and rr.h >= 1:
                work.append(rr)

        _draw(
            placements, work, rect, cut_lines,
            f"Guillotine Adim {step}: '{part.part_id}' {gc}x{gr} izgara blok "
            f"({gc*gr} adet)",
            out / f"g_step_{step}.png",
        )
        step += 1
        if step > 8:
            break

    # Final
    _draw(placements, [], None, [],
          f"Guillotine Sonuc: {len(placements)} parca yerlesti",
          out / "g_final.png")
    print(f"{step} adim + final gorseli uretildi: {out}")


if __name__ == "__main__":
    main()
