"""Coklu plaka orkestrasyonu.

Kullanilan strateji: agirlikli surekli en-iyi-uygun (best-fit greedy)
+ her plaka icin CP-SAT 2D yerlestirme.

Iterasyon:
    1. Mevcut stok adaylari icinden, kalan parcalari en cok kapatma
       potansiyeli olan plakayi sec.
    2. O plaka icin CP-SAT cozucusunu calistir.
    3. Yerlesen parcalari havuzdan dus, plakayi sonuca ekle.
    4. Tum parcalar yerlesene veya stok bitene kadar tekrarla.

Bu yaklasim, tek bir buyuk CP-SAT problemine gore cok daha hizli
calisir ve genelde %95+ alan kullanimi saglar.
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
from .base import OptimizerStrategy
from .cpsat_solver import CPSATSheetSolver


class MultiSheetOrchestrator(OptimizerStrategy):
    """Coklu stok plakasi icin sekansiyel CP-SAT cozumlemesi."""

    def __init__(self, settings: OptimizerSettings):
        super().__init__(settings)
        self.sheet_solver = CPSATSheetSolver(settings)

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
        # Quantity'leri 1'e dusur
        for plates in inventory.values():
            for pl in plates:
                pl.quantity = 1

        # Parca havuzu - asil siparis (quantity > 1 olabilir)
        remaining: List[PartOrder] = [p.model_copy(deep=True) for p in parts]

        sheets_out: List[SheetSolution] = []
        last_status = "UNKNOWN"

        while remaining and any(inventory.values()):
            # Bu turdaki parcalarin tiplerini bul
            type_keys = {self._part_key(p) for p in remaining}

            best_sheet: StockSheet | None = None
            best_key: str | None = None
            best_score = -1

            for key in type_keys:
                if key not in inventory or not inventory[key]:
                    continue
                # Bu tip+kalinlikteki en kucuk yetecek plakayi dene (en-iyi-uygun)
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

            # Bu plakaya yerlestirilebilecek (ayni tip + kalinlik) parcalari sec
            matching = [p for p in remaining if self._part_key(p) == best_key]
            candidate_parts = self._select_candidates_for_sheet(matching, best_sheet)

            sheet_sol, placed_ids, status = self.sheet_solver.solve_single_sheet(
                best_sheet, candidate_parts, kerf
            )
            last_status = status

            if not placed_ids:
                # Bu plakaya higbir sey sigmadi - envantereden cikar, sonraki ile dene
                inventory[best_key].remove(best_sheet)
                continue

            sheets_out.append(sheet_sol)
            inventory[best_key].remove(best_sheet)

            # Yerlesen parcalari havuzdan dus
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

    def _select_candidates_for_sheet(
        self, matching: List[PartOrder], sheet: StockSheet
    ) -> List[PartOrder]:
        """Tek plaka CP-SAT modeline gidecek aday parcalari secer.

        Buyuk siparislerde (1000+ parca) tum parcalari modele gondermek
        CP-SAT'i bogar. Cozuc'un esit tip + kalinlikte tek bir plakaya
        odaklanmasi icin aday havuzu:
          - oncelik azalan,
          - alan azalan,
        siralanir ve hem parca sayisi hem toplam alan acisindan kisitlanir.
        """
        max_count = self.settings.max_parts_per_sheet
        target_area = int(sheet.area_mm2 * self.settings.candidate_area_factor)

        sorted_parts = sorted(
            matching, key=lambda p: (-p.priority, -p.area_mm2)
        )

        selected: List[PartOrder] = []
        total_count = 0
        total_area = 0
        for p in sorted_parts:
            if total_count >= max_count:
                break
            remaining_slots = max_count - total_count
            remaining_area_budget = max(0, target_area - total_area)
            qty_by_count = min(p.quantity, remaining_slots)
            qty_by_area = (
                remaining_area_budget // p.area_mm2 if p.area_mm2 > 0 else 0
            )
            qty = min(qty_by_count, qty_by_area)
            if qty <= 0:
                continue
            selected.append(p.model_copy(update={"quantity": qty}))
            total_count += qty
            total_area += qty * p.area_mm2

        return selected if selected else matching

    @staticmethod
    def _stock_key(s: StockSheet) -> str:
        return f"{s.glass_type.value}|{s.thickness_mm}"

    @staticmethod
    def _part_key(p: PartOrder) -> str:
        return f"{p.glass_type.value}|{p.thickness_mm}"
