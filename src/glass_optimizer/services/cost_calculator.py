"""Maliyet hesaplama servisi.

Endustri standardi mantik:
  - Plaka birim maliyeti * kullanilan plaka adedi -> ham madde maliyeti
  - Kullanilan metrekare * birim cam fiyati -> isleme maliyeti
  - Yerlesemeyen siparis -> kayip ciro / takip listesi
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..domain.models import OptimizationResult


@dataclass
class CostReport:
    raw_material_cost: float       # plaka satin alma toplam
    used_area_m2: float
    waste_area_m2: float
    waste_value: float             # kullanilamayan metrekarenin maliyeti
    cost_per_used_m2: float        # gercek birim maliyet
    unplaced_count: int            # yerlesemeyen parca adedi


def calculate_cost(result: OptimizationResult) -> CostReport:
    used_area_mm2 = result.total_used_area_mm2
    waste_area_mm2 = result.total_waste_area_mm2
    used_m2 = used_area_mm2 / 1_000_000
    waste_m2 = waste_area_mm2 / 1_000_000

    raw_material_cost = 0.0
    cost_per_m2_avg = 0.0
    total_area_for_avg = 0
    for s in result.sheets:
        if not s.placements:
            continue
        raw_material_cost += s.stock.unit_cost
        if s.stock.area_mm2 > 0:
            cost_per_m2_avg += s.stock.unit_cost
            total_area_for_avg += s.stock.area_mm2

    if total_area_for_avg > 0:
        avg_sheet_cost_per_m2 = (
            cost_per_m2_avg / (total_area_for_avg / 1_000_000)
        )
    else:
        avg_sheet_cost_per_m2 = 0.0

    waste_value = waste_m2 * avg_sheet_cost_per_m2
    cost_per_used_m2 = raw_material_cost / used_m2 if used_m2 > 0 else 0.0
    unplaced_count = sum(p.quantity for p in result.unplaced_parts)

    return CostReport(
        raw_material_cost=raw_material_cost,
        used_area_m2=used_m2,
        waste_area_m2=waste_m2,
        waste_value=waste_value,
        cost_per_used_m2=cost_per_used_m2,
        unplaced_count=unplaced_count,
    )
