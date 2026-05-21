"""Hibrit cozucu: MaxRects warm-start + CP-SAT polish.

Adimlar:
    1. MaxRects ile plakanin hizli (milisaniye) baslangic cozumunu uret.
    2. Cozum, CP-SAT modeline AddHint ile beslenir.
    3. CP-SAT `cpsat_polish_time_s` suresince iyilestirme yapar.
    4. Iki cozum karsilastirilir; daha yuksek alan kullanan secilir.

Bu yaklasim, sektorde en yaygin "matheuristik" desenlerden biridir:
hizli sezgisel + tam cozucunun guclendirmesi.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..config.settings import OptimizerSettings
from ..domain.models import (
    KerfSettings,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)
from .base import SheetSolver
from .cpsat_solver import CPSATSheetSolver
from .maxrects_solver import MaxRectsSheetSolver


class HybridSheetSolver(SheetSolver):
    """MaxRects + CP-SAT polish."""

    def __init__(self, settings: OptimizerSettings):
        super().__init__(settings)
        self.maxrects = MaxRectsSheetSolver(settings)

    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
        hints: Optional[List[Placement]] = None,
    ) -> Tuple[SheetSolution, List[str], str]:
        # Asama 1: MaxRects
        heur_sol, heur_placed, _ = self.maxrects.solve_single_sheet(
            sheet, parts, kerf
        )

        if self.settings.cpsat_polish_time_s <= 0:
            return heur_sol, heur_placed, "HYBRID-MAXRECTS"

        # Asama 2: CP-SAT polish - sadece polish suresince
        polish_settings = self.settings.model_copy(
            update={"time_limit_s": self.settings.cpsat_polish_time_s}
        )
        cpsat = CPSATSheetSolver(polish_settings)
        polished_sol, polished_placed, status = cpsat.solve_single_sheet(
            sheet, parts, kerf, hints=heur_sol.placements
        )

        # CP-SAT polish daha iyiyse onu sec
        if polished_sol.used_area_mm2 > heur_sol.used_area_mm2:
            return polished_sol, polished_placed, f"HYBRID-{status}"
        return heur_sol, heur_placed, "HYBRID-MAXRECTS"
