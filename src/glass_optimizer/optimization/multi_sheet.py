"""Coklu plaka orkestrasyonu.

Sira:
    1. Mevcut stok adaylari icinden, kalan parcalarin en cok kapatabilecegi
       plakayi sec (best-fit + greedy).
    2. Sectigi plaka icin seclili SheetSolver'i (MaxRects / CP-SAT / Hybrid)
       calistir.
    3. Yerlesen parcalari havuzdan dus, plakayi sonuca ekle.
    4. Tum parcalar yerlesene veya stok bitene kadar tekrarla.

Strateji `settings.strategy` ile secilir:
    - "hybrid"   : MaxRects + CP-SAT polish (varsayilan, en iyi kalite)
    - "maxrects" : sadece MaxRects (en hizli, binlerce parca icin ideal)
    - "cpsat"    : sadece CP-SAT (kucuk problemler / referans)
"""

from __future__ import annotations

import time
from collections import Counter
from copy import deepcopy
from typing import Dict, List

from ..config.settings import OptimizerSettings
from ..domain.models import (
    KerfSettings,
    OptimizationResult,
    PartOrder,
    SheetSolution,
    StockSheet,
)
from .base import OptimizerStrategy, SheetSolver
from .cpsat_solver import CPSATSheetSolver
from .guillotine_solver import GuillotineSheetSolver
from .hybrid_solver import HybridSheetSolver
from .maxrects_solver import MaxRectsSheetSolver


class MultiSheetOrchestrator(OptimizerStrategy):
    """Coklu stok plakasi icin sekansiyel plaka cozumlemesi."""

    def __init__(
        self,
        settings: OptimizerSettings,
        sheet_solver: SheetSolver | None = None,
    ):
        super().__init__(settings)
        self.sheet_solver = sheet_solver or self._make_solver(settings)

    @staticmethod
    def _make_solver(settings: OptimizerSettings) -> SheetSolver:
        s = settings.strategy.lower()
        if s == "guillotine":
            return GuillotineSheetSolver(settings)
        if s == "maxrects":
            return MaxRectsSheetSolver(settings)
        if s == "cpsat":
            return CPSATSheetSolver(settings)
        if s == "hybrid":
            return HybridSheetSolver(settings)
        raise ValueError(
            f"Bilinmeyen strateji: {settings.strategy!r}. "
            "Gecerli degerler: guillotine, maxrects, cpsat, hybrid."
        )

    def solve(
        self,
        stock: List[StockSheet],
        parts: List[PartOrder],
        kerf: KerfSettings,
    ) -> OptimizationResult:
        t0 = time.perf_counter()

        # Stok envanteri (cam tipi + kalinlik -> mevcut plaka listesi)
        inventory: Dict[str, List[StockSheet]] = {}
        for s in stock:
            key = self._stock_key(s)
            inventory.setdefault(key, []).extend([deepcopy(s) for _ in range(s.quantity)])
        for plates in inventory.values():
            for pl in plates:
                pl.quantity = 1

        remaining: List[PartOrder] = [p.model_copy(deep=True) for p in parts]

        sheets_out: List[SheetSolution] = []
        last_status = "UNKNOWN"

        while remaining and any(inventory.values()):
            type_keys = {self._part_key(p) for p in remaining}

            best_sheet: StockSheet | None = None
            best_key: str | None = None
            best_score = -1

            for key in type_keys:
                if key not in inventory or not inventory[key]:
                    continue
                candidates = sorted(inventory[key], key=lambda s: s.area_mm2)
                for cand in candidates:
                    matching_parts = [p for p in remaining if self._part_key(p) == key]
                    score = sum(p.area_mm2 * p.quantity for p in matching_parts)
                    score = min(score, cand.area_mm2)
                    if score > best_score:
                        best_score = score
                        best_sheet = cand
                        best_key = key

            if best_sheet is None or best_key is None:
                break

            matching = [p for p in remaining if self._part_key(p) == best_key]

            sheet_sol, placed_ids, status = self.sheet_solver.solve_single_sheet(
                best_sheet, matching, kerf
            )
            last_status = status

            if not placed_ids:
                inventory[best_key].remove(best_sheet)
                continue

            sheets_out.append(sheet_sol)
            inventory[best_key].remove(best_sheet)

            placed_counter: Counter = Counter()
            for pid in placed_ids:
                base_id = pid.rsplit("#", 1)[0]
                placed_counter[base_id] += 1

            new_remaining: List[PartOrder] = []
            for p in remaining:
                if p.part_id in placed_counter:
                    n_placed = placed_counter[p.part_id]
                    leftover = p.quantity - n_placed
                    if leftover > 0:
                        leftover_part = p.model_copy(update={"quantity": leftover})
                        new_remaining.append(leftover_part)
                else:
                    new_remaining.append(p)
            remaining = new_remaining

        return OptimizationResult(
            sheets=sheets_out,
            unplaced_parts=remaining,
            total_runtime_s=time.perf_counter() - t0,
            solver_status=last_status,
            kerf=kerf,
        )

    @staticmethod
    def _stock_key(s: StockSheet) -> str:
        return s.match_key

    @staticmethod
    def _part_key(p: PartOrder) -> str:
        return p.match_key
