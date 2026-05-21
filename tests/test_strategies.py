"""Strateji karsilastirma ve smoke testleri."""

from __future__ import annotations

import time

from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.domain.models import KerfSettings, PartOrder, StockSheet
from glass_optimizer.optimization.cpsat_solver import CPSATSheetSolver
from glass_optimizer.optimization.hybrid_solver import HybridSheetSolver
from glass_optimizer.optimization.maxrects_solver import MaxRectsSheetSolver
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator


def _settings(strategy: str = "hybrid", time_limit: float = 3.0) -> OptimizerSettings:
    return OptimizerSettings(
        time_limit_s=time_limit,
        num_workers=4,
        strategy=strategy,
        cpsat_polish_time_s=2.0,
        max_parts_per_sheet=80,
    )


def _no_overlaps(placements) -> bool:
    for a in placements:
        for b in placements:
            if a is b:
                continue
            if (
                a.x_mm < b.x_mm + b.width_mm
                and b.x_mm < a.x_mm + a.width_mm
                and a.y_mm < b.y_mm + b.height_mm
                and b.y_mm < a.y_mm + a.height_mm
            ):
                return False
    return True


def test_maxrects_places_many_uniform_parts_fast():
    sheet = StockSheet(sheet_id="J", width_mm=3000, height_mm=2000, quantity=1)
    parts = [PartOrder(part_id="U", width_mm=400, height_mm=300, quantity=40)]
    solver = MaxRectsSheetSolver(_settings("maxrects"))
    t0 = time.perf_counter()
    sol, placed, status = solver.solve_single_sheet(sheet, parts, KerfSettings())
    elapsed = time.perf_counter() - t0
    assert status == "MAXRECTS"
    assert elapsed < 1.0
    assert len(placed) >= 40  # tamami sigmali (3000*2000=6M, 40*120k=4.8M)
    assert _no_overlaps(sol.placements)


def test_maxrects_no_overlaps_mixed_sizes():
    sheet = StockSheet(sheet_id="J", width_mm=2500, height_mm=2000, quantity=1)
    parts = [
        PartOrder(part_id="A", width_mm=800, height_mm=600, quantity=2),
        PartOrder(part_id="B", width_mm=500, height_mm=400, quantity=5),
        PartOrder(part_id="C", width_mm=300, height_mm=300, quantity=8),
    ]
    solver = MaxRectsSheetSolver(_settings("maxrects"))
    sol, placed, _ = solver.solve_single_sheet(sheet, parts, KerfSettings())
    assert len(placed) >= 10
    assert _no_overlaps(sol.placements)


def test_hybrid_at_least_as_good_as_maxrects():
    sheet = StockSheet(sheet_id="J", width_mm=2500, height_mm=2000, quantity=1)
    parts = [
        PartOrder(part_id="A", width_mm=800, height_mm=600, quantity=2),
        PartOrder(part_id="B", width_mm=500, height_mm=400, quantity=5),
        PartOrder(part_id="C", width_mm=300, height_mm=300, quantity=8),
    ]
    kerf = KerfSettings()

    mr_solver = MaxRectsSheetSolver(_settings("maxrects"))
    hy_solver = HybridSheetSolver(_settings("hybrid"))

    mr_sol, _, _ = mr_solver.solve_single_sheet(sheet, parts, kerf)
    hy_sol, _, _ = hy_solver.solve_single_sheet(sheet, parts, kerf)

    # Hybrid en az MaxRects kadar iyi (warm start ile garanti)
    assert hy_sol.used_area_mm2 >= mr_sol.used_area_mm2
    assert _no_overlaps(hy_sol.placements)


def test_cpsat_accepts_hints():
    sheet = StockSheet(sheet_id="J", width_mm=2000, height_mm=1500, quantity=1)
    parts = [PartOrder(part_id="X", width_mm=900, height_mm=700, quantity=2)]
    kerf = KerfSettings()

    # Once MaxRects ile cozum al
    mr = MaxRectsSheetSolver(_settings("maxrects"))
    mr_sol, _, _ = mr.solve_single_sheet(sheet, parts, kerf)
    assert len(mr_sol.placements) == 2

    # Sonra CP-SAT'a hint olarak ver
    cpsat = CPSATSheetSolver(_settings("cpsat", time_limit=3.0))
    sol, placed, status = cpsat.solve_single_sheet(
        sheet, parts, kerf, hints=mr_sol.placements
    )
    assert len(placed) == 2
    assert _no_overlaps(sol.placements)


def test_orchestrator_strategy_selection():
    stock = [StockSheet(sheet_id="S", width_mm=2000, height_mm=1500, quantity=2)]
    parts = [PartOrder(part_id="A", width_mm=700, height_mm=500, quantity=6)]

    for strat in ("maxrects", "cpsat", "hybrid"):
        result = MultiSheetOrchestrator(_settings(strat, time_limit=2.0)).solve(
            stock, parts, KerfSettings()
        )
        placed_total = sum(len(s.placements) for s in result.sheets)
        assert placed_total == 6, f"{strat} stratejisi tum parcalari yerlestirmedi"


def test_maxrects_scales_to_thousands():
    """Hacim regresyonu: 1000 parca, sub-second beklenir."""
    sheet = StockSheet(sheet_id="J", width_mm=6000, height_mm=3210, quantity=1)
    parts = [PartOrder(part_id="S", width_mm=200, height_mm=150, quantity=1000)]
    t0 = time.perf_counter()
    sol, placed, _ = MaxRectsSheetSolver(_settings("maxrects")).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=0)
    )
    elapsed = time.perf_counter() - t0
    # 6000x3210 = 19.26M / 200x150 = 30k => maksimum 642
    assert len(placed) >= 500
    assert elapsed < 5.0, f"MaxRects 1000 parcayi {elapsed:.2f}s'de cozdu - cok yavas"
