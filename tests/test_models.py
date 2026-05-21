import pytest

from glass_optimizer.domain.enums import GrainConstraint
from glass_optimizer.domain.models import (
    KerfSettings,
    OptimizationResult,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)


def test_stock_area():
    s = StockSheet(sheet_id="A", width_mm=2000, height_mm=1000)
    assert s.area_mm2 == 2_000_000


def test_part_grain_forces_no_rotation():
    p = PartOrder(
        part_id="P1",
        width_mm=100,
        height_mm=200,
        grain=GrainConstraint.FIXED,
        allow_rotation=True,
    )
    assert p.allow_rotation is False


def test_solution_utilization():
    stock = StockSheet(sheet_id="A", width_mm=1000, height_mm=1000)
    placements = [
        Placement(part_id="p1", x_mm=0, y_mm=0, width_mm=500, height_mm=500)
    ]
    sol = SheetSolution(stock=stock, placements=placements)
    assert sol.used_area_mm2 == 250_000
    assert sol.waste_area_mm2 == 750_000
    assert sol.utilization == pytest.approx(0.25)


def test_result_aggregates():
    stock = StockSheet(sheet_id="A", width_mm=1000, height_mm=1000)
    s1 = SheetSolution(
        stock=stock,
        placements=[Placement(part_id="x", x_mm=0, y_mm=0, width_mm=500, height_mm=500)],
    )
    r = OptimizationResult(sheets=[s1], kerf=KerfSettings())
    assert r.sheets_used == 1
    assert r.total_used_area_mm2 == 250_000
