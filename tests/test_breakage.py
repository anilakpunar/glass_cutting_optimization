"""Kirma masasi (breakout) kurallari testleri."""

from __future__ import annotations

import pytest

from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.data.validators import ValidationError, validate_job
from glass_optimizer.domain.models import KerfSettings, PartOrder, StockSheet
from glass_optimizer.optimization.guillotine_solver import GuillotineSheetSolver


def _stock():
    return [StockSheet(sheet_id="S", width_mm=3000, height_mm=2000, quantity=5)]


def test_reject_too_small_part():
    kerf = KerfSettings(min_part_mm=50)
    parts = [PartOrder(part_id="tiny", width_mm=30, height_mm=300, quantity=1)]
    with pytest.raises(ValidationError, match="min_part_mm"):
        validate_job(_stock(), parts, kerf)


def test_reject_extreme_aspect_ratio():
    kerf = KerfSettings(min_part_mm=10, max_aspect_ratio=12.0)
    # 80 x 1200 -> oran 15 > 12
    parts = [PartOrder(part_id="thin", width_mm=80, height_mm=1200, quantity=1)]
    with pytest.raises(ValidationError, match="oran"):
        validate_job(_stock(), parts, kerf)


def test_rules_disabled_allows_small_parts():
    kerf = KerfSettings(min_part_mm=0, max_aspect_ratio=0)
    parts = [PartOrder(part_id="tiny", width_mm=20, height_mm=900, quantity=1)]
    validate_job(_stock(), parts, kerf)  # hata olmamali


def test_avoid_sliver_helper():
    f = GuillotineSheetSolver._avoid_sliver
    # leftover 100 >= 50 -> 3 sutun korunur
    assert f(3, 300, 1000, 0, 50) == 3
    # leftover 0 -> 3 sutun korunur
    assert f(3, 300, 900, 0, 50) == 3
    # leftover 40 < 50 -> sutun azaltilir (2 -> leftover 340)
    assert f(3, 300, 940, 0, 50) == 2
    # kural kapali (min_strip=1) -> 3 korunur
    assert f(3, 300, 940, 0, 1) == 3


def test_guillotine_leaves_no_unbreakable_sliver():
    """min_break_strip aktifken blok kenarinda 0<serit<min arasi kalmamali."""
    sheet = StockSheet(sheet_id="S", width_mm=940, height_mm=2000, quantity=1)
    parts = [PartOrder(part_id="P", width_mm=300, height_mm=500, quantity=9,
                       allow_rotation=False)]
    kerf = KerfSettings(kerf_mm=0, edge_trim_mm=0, min_break_strip_mm=50)
    sol, placed, _ = GuillotineSheetSolver(
        OptimizerSettings(strategy="guillotine")
    ).solve_single_sheet(sheet, parts, kerf)

    # 940 genislikte 300'luk 3. sutun 40mm sliver birakirdi; kural bunu onler.
    # Her satirda en fazla 2 sutun (en sagdaki x2 <= 600) olmali.
    for p in sol.placements:
        assert p.x_mm + p.width_mm <= 600 + 1, "Kirilamaz ince serit olusturuldu"
