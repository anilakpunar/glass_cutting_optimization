from glass_optimizer.domain.models import (
    KerfSettings,
    OptimizationResult,
    Placement,
    SheetSolution,
    StockSheet,
)
from glass_optimizer.services.cost_calculator import calculate_cost
from glass_optimizer.services.cutting_plan import build_cutting_plan
from glass_optimizer.services.waste_analyzer import analyze_waste


def _make_result():
    stock = StockSheet(
        sheet_id="S",
        width_mm=2000,
        height_mm=1000,
        unit_cost=500.0,
        quantity=1,
    )
    placements = [
        Placement(part_id="A#1", x_mm=10, y_mm=10, width_mm=800, height_mm=600),
        Placement(part_id="B#1", x_mm=820, y_mm=10, width_mm=500, height_mm=600),
    ]
    sheet_sol = SheetSolution(stock=stock, placements=placements)
    return OptimizationResult(sheets=[sheet_sol], kerf=KerfSettings())


def test_cost_calculator():
    r = _make_result()
    cost = calculate_cost(r)
    assert cost.raw_material_cost == 500.0
    assert cost.unplaced_count == 0
    assert cost.used_area_m2 > 0
    assert cost.waste_area_m2 > 0


def test_waste_analyzer_finds_right_band_offcut():
    r = _make_result()
    waste = analyze_waste(r, KerfSettings(min_offcut_mm=100))
    # Plakanin sag tarafinda ciddi bos var
    assert len(waste.reusable_offcuts) >= 1


def test_cutting_plan():
    r = _make_result()
    plan = build_cutting_plan(r)
    assert len(plan.sheet_plans) == 1
    assert len(plan.sheet_plans[0].instructions) == 2
    # Sirasi y artarak
    ys = [inst.y_mm for inst in plan.sheet_plans[0].instructions]
    assert ys == sorted(ys)
