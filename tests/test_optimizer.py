from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.domain.models import KerfSettings, PartOrder, StockSheet
from glass_optimizer.optimization.cpsat_solver import CPSATSheetSolver
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator


def _settings():
    return OptimizerSettings(time_limit_s=5.0, num_workers=4)


def test_single_sheet_simple_pack():
    sheet = StockSheet(sheet_id="A", width_mm=2000, height_mm=1000, quantity=1)
    parts = [
        PartOrder(part_id="P1", width_mm=900, height_mm=900, quantity=1),
        PartOrder(part_id="P2", width_mm=900, height_mm=900, quantity=1),
    ]
    solver = CPSATSheetSolver(_settings())
    sol, placed, status = solver.solve_single_sheet(sheet, parts, KerfSettings())
    assert len(placed) == 2
    assert sol.utilization > 0.7
    # parcalar ortusmemeli
    for a in sol.placements:
        for b in sol.placements:
            if a is b:
                continue
            assert not (
                a.x_mm < b.x2_mm
                and b.x_mm < a.x2_mm
                and a.y_mm < b.y2_mm
                and b.y_mm < a.y2_mm
            )


def test_multi_sheet_orchestrator_places_all():
    stock = [
        StockSheet(sheet_id="S1", width_mm=2000, height_mm=1000, quantity=2),
    ]
    parts = [
        PartOrder(part_id="A", width_mm=800, height_mm=800, quantity=3),
    ]
    orchestrator = MultiSheetOrchestrator(_settings())
    result = orchestrator.solve(stock, parts, KerfSettings())
    placed_total = sum(len(s.placements) for s in result.sheets)
    assert placed_total == 3
    assert not result.unplaced_parts


def test_rotation_used_when_needed():
    # Parca 1500x500. Plaka 1500x500 ile bire bir uyar.
    sheet = StockSheet(sheet_id="S", width_mm=1520, height_mm=520, quantity=1)
    parts = [
        PartOrder(
            part_id="ROT",
            width_mm=500,
            height_mm=1500,
            quantity=1,
            allow_rotation=True,
        )
    ]
    solver = CPSATSheetSolver(_settings())
    sol, placed, _ = solver.solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=10)
    )
    assert len(placed) == 1
    p = sol.placements[0]
    # Rotasyon sonrasi width 1500, height 500 olmali
    assert p.width_mm == 1500
    assert p.height_mm == 500
