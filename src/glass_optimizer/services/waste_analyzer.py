"""Fire (waste) analizi.

Plaka basina ve toplam fire metriklerini cikarir, ayrica yeniden
kullanilabilir buyuk parcalari (offcut) tespit eder.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from ..domain.models import KerfSettings, OptimizationResult, Placement, SheetSolution


@dataclass
class OffCut:
    sheet_id: str
    x_mm: int
    y_mm: int
    width_mm: int
    height_mm: int

    @property
    def area_mm2(self) -> int:
        return self.width_mm * self.height_mm

    @property
    def area_m2(self) -> float:
        return self.area_mm2 / 1_000_000


@dataclass
class WasteReport:
    total_stock_m2: float
    total_used_m2: float
    total_waste_m2: float
    overall_utilization: float           # 0..1
    per_sheet_utilization: List[Tuple[str, float]] = field(default_factory=list)
    reusable_offcuts: List[OffCut] = field(default_factory=list)
    reusable_offcut_m2: float = 0.0


def analyze_waste(result: OptimizationResult, kerf: KerfSettings) -> WasteReport:
    per_sheet = [(s.stock.sheet_id, s.utilization) for s in result.sheets]

    offcuts: List[OffCut] = []
    for sheet in result.sheets:
        offcuts.extend(_extract_reusable_offcuts(sheet, kerf))

    reusable_m2 = sum(o.area_m2 for o in offcuts)

    return WasteReport(
        total_stock_m2=result.total_stock_area_mm2 / 1_000_000,
        total_used_m2=result.total_used_area_mm2 / 1_000_000,
        total_waste_m2=result.total_waste_area_mm2 / 1_000_000,
        overall_utilization=result.overall_utilization,
        per_sheet_utilization=per_sheet,
        reusable_offcuts=offcuts,
        reusable_offcut_m2=reusable_m2,
    )


def _extract_reusable_offcuts(
    sheet: SheetSolution, kerf: KerfSettings
) -> List[OffCut]:
    """Plakanin sag ve ust bandindaki kullanilabilir buyuk fireleri bulur.

    Tam (recursive) bos alan ayristirmasi yerine, sektorde yaygin olan
    'maxima rectangle' yaklasiminin basitlestirilmis hali: yerlesen
    parcalarin sag kenari ile plakanin sag kenari arasindaki dikey serit
    ve ust kenari ile ust serit incelenir.
    """
    if not sheet.placements:
        return []

    W = sheet.stock.width_mm - kerf.edge_trim_mm
    H = sheet.stock.height_mm - kerf.edge_trim_mm
    x0 = kerf.edge_trim_mm
    y0 = kerf.edge_trim_mm

    max_x = max(p.x2_mm for p in sheet.placements)
    max_y = max(p.y2_mm for p in sheet.placements)

    candidates: List[OffCut] = []

    right_w = W - max_x
    right_h = H - y0
    if right_w >= kerf.min_offcut_mm and right_h >= kerf.min_offcut_mm:
        candidates.append(
            OffCut(
                sheet_id=sheet.stock.sheet_id,
                x_mm=max_x,
                y_mm=y0,
                width_mm=right_w,
                height_mm=right_h,
            )
        )

    top_w = max_x - x0
    top_h = H - max_y
    if top_w >= kerf.min_offcut_mm and top_h >= kerf.min_offcut_mm:
        candidates.append(
            OffCut(
                sheet_id=sheet.stock.sheet_id,
                x_mm=x0,
                y_mm=max_y,
                width_mm=top_w,
                height_mm=top_h,
            )
        )

    return candidates
