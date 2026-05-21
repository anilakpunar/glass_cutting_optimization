"""Optimizasyon strateji arayuzleri.

Iki seviye var:
  - SheetSolver        : tek bir plaka uzerinde yerlestirme
                         (MaxRects / CP-SAT / Hybrid)
  - OptimizerStrategy  : tum siparisi coklu plaka uzerinde cozer
                         (MultiSheetOrchestrator)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from ..config.settings import OptimizerSettings
from ..domain.models import (
    KerfSettings,
    OptimizationResult,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)


class SheetSolver(ABC):
    """Tek plaka cozucu arayuzu.

    Implementasyonlar opsiyonel olarak `hints` (onceki cozumden gelen
    yerlesim ipuclari) kabul edebilir; desteklemeyenler sessizce
    yok sayar.
    """

    def __init__(self, settings: OptimizerSettings):
        self.settings = settings

    @abstractmethod
    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
        hints: Optional[List[Placement]] = None,
    ) -> Tuple[SheetSolution, List[str], str]: ...


class OptimizerStrategy(ABC):
    """Coklu plaka cozucu arayuzu."""

    def __init__(self, settings: OptimizerSettings):
        self.settings = settings

    @abstractmethod
    def solve(
        self,
        stock: List[StockSheet],
        parts: List[PartOrder],
        kerf: KerfSettings,
    ) -> OptimizationResult: ...
