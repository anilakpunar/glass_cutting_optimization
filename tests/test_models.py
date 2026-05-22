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


def test_match_key_falls_back_to_type_thickness():
    s = StockSheet(sheet_id="A", width_mm=100, height_mm=100, thickness_mm=4.0)
    p = PartOrder(part_id="P", width_mm=50, height_mm=50, thickness_mm=4.0)
    assert s.match_key == p.match_key == "float|4.0"


def test_match_key_uses_material_when_set():
    s = StockSheet(sheet_id="A", width_mm=100, height_mm=100, material="TEC15")
    p = PartOrder(part_id="P", width_mm=50, height_mm=50, material="TEC15")
    other = PartOrder(part_id="Q", width_mm=50, height_mm=50, material="EKOPRO")
    # Ayni glass_type+kalinlik olsa da material farkliysa eslesmemeli
    assert s.match_key == p.match_key == "TEC15"
    assert other.match_key != s.match_key


def test_result_aggregates():
    stock = StockSheet(sheet_id="A", width_mm=1000, height_mm=1000)
    s1 = SheetSolution(
        stock=stock,
        placements=[Placement(part_id="x", x_mm=0, y_mm=0, width_mm=500, height_mm=500)],
    )
    r = OptimizationResult(sheets=[s1], kerf=KerfSettings())
    assert r.sheets_used == 1
    assert r.total_used_area_mm2 == 250_000
