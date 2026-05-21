"""Kesim plani uretimi.

Atolyede operatorun takip edebilecegi sirali kesim talimatlarini
olusturur. Sektor pratigi:
  1. Plakayi makineye yerlestir.
  2. Sol-alt referans noktasindan baslayarak parcalari satir satir kes.
  3. Her kesimde kerf payi dikkate al.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ..domain.models import OptimizationResult, Placement, SheetSolution


@dataclass
class CutInstruction:
    step: int
    description: str
    part_id: str
    x_mm: int
    y_mm: int
    width_mm: int
    height_mm: int


@dataclass
class SheetPlan:
    sheet_id: str
    instructions: List[CutInstruction] = field(default_factory=list)


@dataclass
class CuttingPlan:
    sheet_plans: List[SheetPlan] = field(default_factory=list)


def build_cutting_plan(result: OptimizationResult) -> CuttingPlan:
    plan = CuttingPlan()
    for sheet in result.sheets:
        sp = SheetPlan(sheet_id=sheet.stock.sheet_id)
        # Operator referansi: once alttan ust e (y artarak), sonra soldan saga (x)
        sorted_placements: List[Placement] = sorted(
            sheet.placements, key=lambda p: (p.y_mm, p.x_mm)
        )
        for i, p in enumerate(sorted_placements, start=1):
            sp.instructions.append(
                CutInstruction(
                    step=i,
                    description=(
                        f"Konum (x={p.x_mm}, y={p.y_mm}) - "
                        f"{p.width_mm}x{p.height_mm} mm "
                        f"[{p.orientation.value}]"
                    ),
                    part_id=p.part_id,
                    x_mm=p.x_mm,
                    y_mm=p.y_mm,
                    width_mm=p.width_mm,
                    height_mm=p.height_mm,
                )
            )
        plan.sheet_plans.append(sp)
    return plan
