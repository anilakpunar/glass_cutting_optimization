"""Guillotine-kisitli homojen blok yerlestirme.

NEDEN GUILLOTINE?
-----------------
Cam kesim koprusu DUZ (edge-to-edge) kesim yapar: bicak plakayi bir
kenardan diger kenara kadar boler. Bu yuzden yerlesim **guillotine
kesilebilir** olmak ZORUNDADIR:
    once bir yonde bastan basa kesim, sonra olusan seritlerde ara kesimler.

Bu, klasik (serbest) 2D bin-packing DEGILDIR; guillotine-kisitli 2D
cutting-stock problemidir. MaxRects gibi serbest paketleyiciler bu
kisiti saglamaz, bu yuzden cam kesim icin bu cozucu kullanilir.

NEDEN HOMOJEN BLOK?
-------------------
Atolye verimliligi icin bir plakadaki parca CESITLILIGI az olmalidir.
Bu cozucu once bir bolgeye TEK olcuden olabildigince cok parcayi izgara
(grid) seklinde yerlestirir, ancak ondan sonra kalan guillotine
artiklarina sonraki olculeri doldurur.

ALGORITMA (recursive guillotine):
    pack(rect):
        1. Aday parcalar arasinda bu rect'i en cok dolduran tek-tip
           izgara blogunu sec (gc sutun x gr satir; iki yon de denenir).
        2. Blogu rect'in sol-altina yerlestir.
        3. Kalani guillotine ile iki dikdortgene bol (A veya B kesim);
           daha buyuk kullanilabilir artigi koruyan secilir.
        4. Iki artik icin pack() ozyinele.

Grid blok (sutunlara sonra satirlara kesim) + ozyinemeli dikdortgen
bolme => tum kesimler edge-to-edge: yerlesim her zaman guillotine'dir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..domain.enums import CutOrientation, GrainConstraint
from ..domain.models import (
    KerfSettings,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)
from .base import SheetSolver


@dataclass
class _Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h


# (part, pw, ph, rotated, gc, gr)
_Block = Tuple[PartOrder, int, int, bool, int, int]


class GuillotineSheetSolver(SheetSolver):
    """Recursive guillotine homojen-blok cozucu."""

    MIN_DIM = 1

    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
        hints: Optional[List[Placement]] = None,
    ) -> Tuple[SheetSolution, List[str], str]:
        usable = _Rect(
            kerf.edge_trim_mm,
            kerf.edge_trim_mm,
            sheet.width_mm - 2 * kerf.edge_trim_mm,
            sheet.height_mm - 2 * kerf.edge_trim_mm,
        )
        if usable.w < self.MIN_DIM or usable.h < self.MIN_DIM:
            return SheetSolution(stock=sheet), [], "NO_USABLE_AREA"

        pool: Dict[str, int] = {p.part_id: p.quantity for p in parts}
        used_count: Dict[str, int] = {p.part_id: 0 for p in parts}
        placements: List[Placement] = []

        self._pack(usable, parts, pool, kerf, placements, used_count)

        placed_ids = [pl.part_id for pl in placements]
        return (
            SheetSolution(stock=sheet, placements=placements),
            placed_ids,
            "GUILLOTINE",
        )

    def _pack(
        self,
        rect: _Rect,
        parts: List[PartOrder],
        pool: Dict[str, int],
        kerf: KerfSettings,
        placements: List[Placement],
        used_count: Dict[str, int],
    ) -> None:
        # Kirma masasinda koparilamayacak kadar ince bolgeleri isleme:
        # bu serit fire kalir, parcalanmaya calisilmaz.
        min_strip = max(self.MIN_DIM, kerf.min_break_strip_mm)
        if rect.w < min_strip or rect.h < min_strip:
            return

        block = self._best_block(rect, parts, pool, kerf)
        if block is None:
            return

        part, pw, ph, rotated, gc, gr = block
        k = kerf.kerf_mm

        # Izgara blogunu sol-alttan yerlestir
        for r in range(gr):
            for c in range(gc):
                if pool[part.part_id] <= 0:
                    break
                px = rect.x + c * (pw + k)
                py = rect.y + r * (ph + k)
                used_count[part.part_id] += 1
                placements.append(
                    Placement(
                        part_id=f"{part.part_id}#{used_count[part.part_id]}",
                        x_mm=px,
                        y_mm=py,
                        width_mm=pw,
                        height_mm=ph,
                        orientation=(
                            CutOrientation.ROTATED_90
                            if rotated
                            else CutOrientation.NORMAL
                        ),
                    )
                )
                pool[part.part_id] -= 1

        block_w = gc * pw + (gc - 1) * k
        block_h = gr * ph + (gr - 1) * k

        top_h = rect.h - block_h - k
        right_w = rect.w - block_w - k

        # Iki guillotine bolme secenegi; daha buyuk artigi koruyani sec.
        # A (yatay-once): ust serit tum genisligi, sag serit blok yuksekligini alir
        topA = _Rect(rect.x, rect.y + block_h + k, rect.w, top_h)
        rightA = _Rect(rect.x + block_w + k, rect.y, right_w, block_h)
        # B (dikey-once): sag serit tum yuksekligi, ust serit blok genisligini alir
        topB = _Rect(rect.x, rect.y + block_h + k, block_w, top_h)
        rightB = _Rect(rect.x + block_w + k, rect.y, right_w, rect.h)

        scoreA = max(self._eff_area(topA, min_strip), self._eff_area(rightA, min_strip))
        scoreB = max(self._eff_area(topB, min_strip), self._eff_area(rightB, min_strip))

        if scoreA >= scoreB:
            top, right = topA, rightA
        else:
            top, right = topB, rightB

        # Buyuk artigi once isle (daha iyi blok secimi sansi)
        first, second = (top, right) if top.area >= right.area else (right, top)
        self._pack(first, parts, pool, kerf, placements, used_count)
        self._pack(second, parts, pool, kerf, placements, used_count)

    def _eff_area(self, rect: _Rect, min_strip: int = 1) -> int:
        if rect.w < min_strip or rect.h < min_strip:
            return 0
        return rect.area

    def _best_block(
        self,
        rect: _Rect,
        parts: List[PartOrder],
        pool: Dict[str, int],
        kerf: KerfSettings,
    ) -> Optional[_Block]:
        """Bu rect'i en cok dolduran tek-tip izgara blogunu sec.

        Skor = (kapsanan_alan, oncelik). Kapsanan alan birincil olcuttur:
        boylece once en cok parca sigan tek olcu secilir (fire + cesitlilik
        azaltma). Esitlikte yuksek oncelikli (acil) siparis one cikar.
        """
        k = kerf.kerf_mm
        min_strip = max(self.MIN_DIM, kerf.min_break_strip_mm)
        best: Optional[_Block] = None
        best_key: Optional[Tuple[int, int]] = None

        for p in parts:
            if pool[p.part_id] <= 0:
                continue

            orientations = [(p.width_mm, p.height_mm, False)]
            if (
                p.allow_rotation
                and p.grain != GrainConstraint.FIXED
                and p.width_mm != p.height_mm
            ):
                orientations.append((p.height_mm, p.width_mm, True))

            for pw, ph, rotated in orientations:
                if pw > rect.w or ph > rect.h:
                    continue
                max_cols = (rect.w + k) // (pw + k)
                max_rows = (rect.h + k) // (ph + k)
                if max_cols <= 0 or max_rows <= 0:
                    continue

                cap = max_cols * max_rows
                gc, gr = self._fit_grid(max_cols, max_rows, min(cap, pool[p.part_id]))
                # Kirma kurali: blok kenarinda koparilamayacak ince serit
                # (sliver) birakma. Sutun/satir sayisini, kalan serit 0 veya
                # >= min_strip olacak sekilde ayarla.
                gc = self._avoid_sliver(gc, pw, rect.w, k, min_strip)
                gr = self._avoid_sliver(gr, ph, rect.h, k, min_strip)
                if gc * gr <= 0:
                    continue

                coverage = gc * gr * pw * ph
                key = (coverage, p.priority)
                if best_key is None or key > best_key:
                    best_key = key
                    best = (p, pw, ph, rotated, gc, gr)

        return best

    @staticmethod
    def _avoid_sliver(count: int, cell: int, avail: int, k: int, min_strip: int) -> int:
        """Kalan seridi 0 veya >= min_strip yapacak en buyuk sayiyi dondurur.

        Blok ile bolge kenari arasinda kirma masasinda koparilamayacak ince
        bir serit (0 < serit < min_strip) kalmasini engeller.
        """
        while count > 0:
            leftover = avail - (count * cell + (count - 1) * k)
            if leftover <= 0 or leftover >= min_strip:
                return count
            count -= 1
        return 0

    @staticmethod
    def _fit_grid(max_cols: int, max_rows: int, n: int) -> Tuple[int, int]:
        """gc*gr <= n olacak sekilde en buyuk izgara (gc<=max_cols, gr<=max_rows)."""
        if n <= 0:
            return 0, 0
        if n >= max_cols * max_rows:
            return max_cols, max_rows
        best = (0, 0)
        best_prod = 0
        for gc in range(1, max_cols + 1):
            gr = min(max_rows, n // gc)
            if gr <= 0:
                continue
            prod = gc * gr
            if prod > best_prod:
                best_prod = prod
                best = (gc, gr)
        return best
