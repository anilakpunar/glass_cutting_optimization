"""Optimizasyon strateji arayuzu."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..config.settings import OptimizerSettings
from ..domain.models import KerfSettings, OptimizationResult, PartOrder, StockSheet


class OptimizerStrategy(ABC):
    """Tum cozucu stratejilerin uygulamasi gereken arayuz."""

    def __init__(self, settings: OptimizerSettings):
        self.settings = settings

    @abstractmethod
    def solve(
        self,
        stock: List[StockSheet],
        parts: List[PartOrder],
        kerf: KerfSettings,
    ) -> OptimizationResult: ...
