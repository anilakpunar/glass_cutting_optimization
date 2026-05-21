"""MaxRects 2D yerlestirme heuristiği.

Jylänki'nin "A Thousand Ways to Pack the Bin" (2010) calismasindaki
Best Short Side Fit (BSSF) varyanti. Sektorde fiili standart heuristik:

Algoritma:
    1. Plaka, baslangicta tek bir bos dikdortgen olarak temsil edilir.
    2. Parcalar oncelik DESC, alan DESC sirasinda islenir.
    3. Her parca icin tum bos dikdortgenler arasinda en az kalinti
       (kisa kenar) birakan yer secilir; rotasyon izinliyse iki yon
       de denenir.
    4. Yerlestirildikten sonra, parca ile kesisen TUM bos dikdortgenler
       4 yeni bos dikdortgene bolunur (MaxRects ozelligi).
    5. Baska bir bos dikdortgenin icinde kalan dikdortgenler prune
       edilir (gereksiz overhead'i temizler).

Karmasiklik: O(n^2) ile O(n^3) arasi pratikte, binlerce parca icin
saniye altinda calisir.

Sektorde tipik verim: %85-92 (homojen siparislerde %90+).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..config.settings import OptimizerSettings
from ..domain.enums import CutOrientation, GrainConstraint
from ..domain.models import (
    KerfSettings,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)
from .base import SheetSolver
from .cpsat_solver import _ExpandedPart, _expand


@dataclass
class _FreeRect:
    x: int
    y: int
    w: int
    h: int


class MaxRectsSheetSolver(SheetSolver):
    """MaxRects Best Short Side Fit ile tek plaka yerlestirme."""

    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
        hints: Optional[List[Placement]] = None,
    ) -> Tuple[SheetSolution, List[str], str]:
        expanded = _expand(parts)
        if not expanded:
            return SheetSolution(stock=sheet), [], "EMPTY"

        # Oncelik DESC, sonra alan DESC ile sirala (first-fit decreasing)
        expanded.sort(
            key=lambda e: (-e.base.priority, -(e.base.width_mm * e.base.height_mm))
        )

        x0 = kerf.edge_trim_mm
        y0 = kerf.edge_trim_mm
        W = sheet.width_mm - 2 * kerf.edge_trim_mm
        H = sheet.height_mm - 2 * kerf.edge_trim_mm

        if W <= 0 or H <= 0:
            return SheetSolution(stock=sheet), [], "NO_USABLE_AREA"

        free_rects: List[_FreeRect] = [_FreeRect(x0, y0, W, H)]
        placements: List[Placement] = []
        placed_ids: List[str] = []

        k = kerf.kerf_mm

        for ep in expanded:
            p = ep.base
            w_eff = p.width_mm + k
            h_eff = p.height_mm + k
            allow_rot = p.allow_rotation and p.grain != GrainConstraint.FIXED

            best = self._find_best_fit(free_rects, w_eff, h_eff, allow_rot)
            if best is None:
                continue

            x, y, used_w, used_h, rotated = best
            self._split_overlapping(free_rects, x, y, used_w, used_h)
            self._prune_contained(free_rects)

            placements.append(
                Placement(
                    part_id=ep.instance_id,
                    x_mm=x,
                    y_mm=y,
                    width_mm=used_w - k,
                    height_mm=used_h - k,
                    orientation=(
                        CutOrientation.ROTATED_90
                        if rotated
                        else CutOrientation.NORMAL
                    ),
                )
            )
            placed_ids.append(ep.instance_id)

        return (
            SheetSolution(stock=sheet, placements=placements),
            placed_ids,
            "MAXRECTS",
        )

    @staticmethod
    def _find_best_fit(
        free_rects: List[_FreeRect],
        w: int,
        h: int,
        allow_rotation: bool,
    ) -> Optional[Tuple[int, int, int, int, bool]]:
        """Best Short Side Fit: en kucuk kalinti (kisa kenar) skoru."""
        best: Optional[Tuple[int, int, int, int, bool]] = None
        best_short = float("inf")
        best_long = float("inf")

        for r in free_rects:
            if w <= r.w and h <= r.h:
                lw = r.w - w
                lh = r.h - h
                short = lw if lw < lh else lh
                long_ = lh if lw < lh else lw
                if short < best_short or (short == best_short and long_ < best_long):
                    best_short = short
                    best_long = long_
                    best = (r.x, r.y, w, h, False)
            if allow_rotation and h <= r.w and w <= r.h:
                lw = r.w - h
                lh = r.h - w
                short = lw if lw < lh else lh
                long_ = lh if lw < lh else lw
                if short < best_short or (short == best_short and long_ < best_long):
                    best_short = short
                    best_long = long_
                    best = (r.x, r.y, h, w, True)

        return best

    @staticmethod
    def _split_overlapping(
        free_rects: List[_FreeRect],
        px: int,
        py: int,
        pw: int,
        ph: int,
    ) -> None:
        """Kesisen tum bos dikdortgenleri 4 stripe parcala (MaxRects ozelligi)."""
        i = 0
        original_len = len(free_rects)
        while i < original_len:
            r = free_rects[i]
            if (
                px >= r.x + r.w
                or px + pw <= r.x
                or py >= r.y + r.h
                or py + ph <= r.y
            ):
                i += 1
                continue

            # Kesisen rect'i kaldir
            free_rects.pop(i)
            original_len -= 1

            # Sol stripe
            if px > r.x:
                free_rects.append(_FreeRect(r.x, r.y, px - r.x, r.h))
            # Sag stripe
            if px + pw < r.x + r.w:
                free_rects.append(
                    _FreeRect(px + pw, r.y, r.x + r.w - (px + pw), r.h)
                )
            # Alt stripe
            if py > r.y:
                free_rects.append(_FreeRect(r.x, r.y, r.w, py - r.y))
            # Ust stripe
            if py + ph < r.y + r.h:
                free_rects.append(
                    _FreeRect(r.x, py + ph, r.w, r.y + r.h - (py + ph))
                )

    @staticmethod
    def _prune_contained(free_rects: List[_FreeRect]) -> None:
        """Baska bir bos rect icine tamamen giren rect'leri kaldir."""
        i = 0
        while i < len(free_rects):
            r1 = free_rects[i]
            removed_i = False
            j = i + 1
            while j < len(free_rects):
                r2 = free_rects[j]
                if (
                    r2.x <= r1.x
                    and r2.y <= r1.y
                    and r2.x + r2.w >= r1.x + r1.w
                    and r2.y + r2.h >= r1.y + r1.h
                ):
                    free_rects.pop(i)
                    removed_i = True
                    break
                if (
                    r1.x <= r2.x
                    and r1.y <= r2.y
                    and r1.x + r1.w >= r2.x + r2.w
                    and r1.y + r1.h >= r2.y + r2.h
                ):
                    free_rects.pop(j)
                    continue
                j += 1
            if not removed_i:
                i += 1
