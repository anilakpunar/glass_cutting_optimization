"""Guillotine cozucu testleri: gecerlilik, homojenlik, ortusmeme."""

from __future__ import annotations

from typing import List

from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.domain.models import KerfSettings, PartOrder, Placement, StockSheet
from glass_optimizer.optimization.guillotine_solver import GuillotineSheetSolver
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator


def _settings() -> OptimizerSettings:
    return OptimizerSettings(strategy="guillotine")


def _no_overlaps(placements: List[Placement]) -> bool:
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


def _is_guillotine(placements: List[Placement]) -> bool:
    """Yerlesimin guillotine kesilebilir olup olmadigini ozyinemeli dogrular.

    Bir dikdortgen kumesi guillotine'dir eger:
      - 0 veya 1 parca iceriyorsa, ya da
      - hicbir parcayi kesmeyen, kumeyi iki bos olmayan gruba ayiran
        dikey VEYA yatay bir tam kesim cizgisi varsa ve her grup kendi
        icinde guillotine ise.
    """
    rects = [(p.x_mm, p.y_mm, p.x_mm + p.width_mm, p.y_mm + p.height_mm) for p in placements]
    return _guillotine_rec(rects)


def _guillotine_rec(rects) -> bool:
    if len(rects) <= 1:
        return True

    # Dikey kesimler
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    for x in xs:
        left = [r for r in rects if r[2] <= x]
        right = [r for r in rects if r[0] >= x]
        if left and right and len(left) + len(right) == len(rects):
            return _guillotine_rec(left) and _guillotine_rec(right)

    # Yatay kesimler
    ys = sorted({r[1] for r in rects} | {r[3] for r in rects})
    for y in ys:
        bottom = [r for r in rects if r[3] <= y]
        top = [r for r in rects if r[1] >= y]
        if bottom and top and len(bottom) + len(top) == len(rects):
            return _guillotine_rec(bottom) and _guillotine_rec(top)

    return False


def test_guillotine_uniform_grid_full():
    # 2000x1000 plaka, 400x500 parca: 5 sutun x 2 satir = 10 sigar
    sheet = StockSheet(sheet_id="S", width_mm=2000, height_mm=1000, quantity=1)
    parts = [PartOrder(part_id="A", width_mm=400, height_mm=500, quantity=20)]
    sol, placed, status = GuillotineSheetSolver(_settings()).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=0)
    )
    assert status == "GUILLOTINE"
    assert len(placed) == 10
    assert sol.utilization == 1.0
    assert _no_overlaps(sol.placements)
    assert _is_guillotine(sol.placements)


def test_guillotine_mixed_sizes_is_guillotine():
    sheet = StockSheet(sheet_id="S", width_mm=3000, height_mm=2000, quantity=1)
    parts = [
        PartOrder(part_id="BIG", width_mm=900, height_mm=600, quantity=4),
        PartOrder(part_id="MID", width_mm=500, height_mm=400, quantity=8),
        PartOrder(part_id="SML", width_mm=300, height_mm=250, quantity=12),
    ]
    sol, placed, _ = GuillotineSheetSolver(_settings()).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=3, edge_trim_mm=10)
    )
    assert len(placed) > 0
    assert _no_overlaps(sol.placements)
    assert _is_guillotine(sol.placements), "Yerlesim guillotine kesilebilir degil!"


def test_guillotine_homogeneity_first():
    """En cok sigan tek olcu once ve buyuk blok halinde yerlesmeli."""
    sheet = StockSheet(sheet_id="S", width_mm=2000, height_mm=2000, quantity=1)
    parts = [
        PartOrder(part_id="DOMINANT", width_mm=500, height_mm=500, quantity=16),
        PartOrder(part_id="FILLER", width_mm=200, height_mm=200, quantity=20),
    ]
    sol, _, _ = GuillotineSheetSolver(_settings()).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=0)
    )
    # 2000x2000'e 500x500'den 4x4=16 tam sigar -> tum plakayi DOMINANT doldurur
    dom = [p for p in sol.placements if p.part_id.startswith("DOMINANT")]
    assert len(dom) == 16
    assert sol.utilization == 1.0


def test_guillotine_rotation():
    # Parca 1500x400, plaka 1600x1500. Dik (rotated) yerlesince daha cok sigar.
    sheet = StockSheet(sheet_id="S", width_mm=1600, height_mm=1500, quantity=1)
    parts = [
        PartOrder(part_id="R", width_mm=1500, height_mm=400, quantity=3, allow_rotation=True)
    ]
    sol, placed, _ = GuillotineSheetSolver(_settings()).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=0)
    )
    assert len(placed) >= 3
    assert _is_guillotine(sol.placements)


def test_guillotine_orchestrator_places_all():
    stock = [StockSheet(sheet_id="S", width_mm=2000, height_mm=1500, quantity=3)]
    parts = [
        PartOrder(part_id="A", width_mm=600, height_mm=500, quantity=10),
        PartOrder(part_id="B", width_mm=400, height_mm=300, quantity=8),
    ]
    result = MultiSheetOrchestrator(_settings()).solve(stock, parts, KerfSettings())
    placed_total = sum(len(s.placements) for s in result.sheets)
    assert placed_total == 18
    assert not result.unplaced_parts
    for s in result.sheets:
        assert _is_guillotine(s.placements)


def test_guillotine_respects_fixed_grain_no_rotation():
    from glass_optimizer.domain.enums import GrainConstraint

    sheet = StockSheet(sheet_id="S", width_mm=1000, height_mm=1000, quantity=1)
    parts = [
        PartOrder(
            part_id="P", width_mm=300, height_mm=200, quantity=4,
            grain=GrainConstraint.FIXED,
        )
    ]
    sol, _, _ = GuillotineSheetSolver(_settings()).solve_single_sheet(
        sheet, parts, KerfSettings(kerf_mm=0, edge_trim_mm=0)
    )
    # grain=fixed -> hicbir parca donmemeli
    for p in sol.placements:
        assert p.width_mm == 300 and p.height_mm == 200
