"""CP-SAT tabanli tek plaka 2D yerlestirme cozucusu.

Model ozeti
-----------
Verilen tek bir stok plakasi ve bir parca havuzu uzerinden, hangi
parcalarin yerlestirilecegi ve nereye konacagi tam sayi degiskenleri
ile aranir.

Her parca icin:
  - placed     : Bool, yerlestirildi mi?
  - rotated    : Bool, 90 derece donduruldu mu? (izinli ise)
  - x_start    : Int, sol kenar (mm)
  - y_start    : Int, alt kenar (mm)

Kisitlar:
  - placed=True ise x_start + w_eff <= W - edge_trim
  - placed=True ise y_start + h_eff <= H - edge_trim
  - Tum yerlesik parcalar arasinda AddNoOverlap2D
  - Kerf parca olculerine eklenir (testere kalinligi guvenligi)

Amac fonksiyonu
---------------
  minimize_waste  -> yerlesen alani (oncelik agirlikli) maksimize et
  maximize_value  -> oncelige gore agirliklandirilmis alan
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ortools.sat.python import cp_model

from ..config.settings import OptimizerSettings
from ..domain.enums import CutOrientation, GrainConstraint
from ..domain.models import (
    KerfSettings,
    PartOrder,
    Placement,
    SheetSolution,
    StockSheet,
)


@dataclass
class _ExpandedPart:
    """Quantity parametresi acilmis tekil parca ornegi."""

    instance_id: str
    base: PartOrder


def _expand(parts: List[PartOrder]) -> List[_ExpandedPart]:
    out: List[_ExpandedPart] = []
    for p in parts:
        for idx in range(p.quantity):
            out.append(_ExpandedPart(instance_id=f"{p.part_id}#{idx + 1}", base=p))
    return out


class CPSATSheetSolver:
    """Tek bir plaka uzerinde maksimum yerlestirme yapan CP-SAT cozucu."""

    def __init__(self, settings: OptimizerSettings):
        self.settings = settings

    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
    ) -> Tuple[SheetSolution, List[str], str]:
        """Tek plaka icin cozum uretir.

        Returns
        -------
        (cozum, yerlesen parca instance_id listesi, solver_status)
        """

        expanded = _expand(parts)
        if not expanded:
            return SheetSolution(stock=sheet), [], "EMPTY"

        usable_w = sheet.width_mm - 2 * kerf.edge_trim_mm
        usable_h = sheet.height_mm - 2 * kerf.edge_trim_mm
        x_offset = kerf.edge_trim_mm
        y_offset = kerf.edge_trim_mm
        k = kerf.kerf_mm

        model = cp_model.CpModel()

        x_intervals: List[cp_model.IntervalVar] = []
        y_intervals: List[cp_model.IntervalVar] = []

        # Her parca icin metadata
        placed_vars: List[cp_model.IntVar] = []
        rot_vars: List[Optional[cp_model.IntVar]] = []
        x_starts: List[Tuple[cp_model.IntVar, cp_model.IntVar]] = []  # (normal, rotated) - rotated None ise sadece normal
        y_starts: List[Tuple[cp_model.IntVar, cp_model.IntVar]] = []
        pres_normal: List[cp_model.IntVar] = []
        pres_rotated: List[Optional[cp_model.IntVar]] = []
        weights: List[int] = []

        for i, ep in enumerate(expanded):
            p = ep.base
            w_eff = p.width_mm + k
            h_eff = p.height_mm + k

            fits_normal = w_eff <= usable_w + k and h_eff <= usable_h + k
            # Kerf eklemesi son parca icin tasmamali; gercekte parca kerf'siz
            # de yerlesir, fakat hesap kolayligi icin kerf'i parca boyutuna
            # ekliyoruz. Bu, kenarda kerf payi birakilmis oldugu icin
            # guvenlidir (edge_trim_mm kapsar).
            fits_normal = p.width_mm <= usable_w and p.height_mm <= usable_h
            fits_rotated = (
                p.allow_rotation
                and p.grain != GrainConstraint.FIXED
                and p.height_mm <= usable_w
                and p.width_mm <= usable_h
            )

            if not fits_normal and not fits_rotated:
                # Bu plaka uzerinde hic sigmiyor; placed = False olarak ekleme.
                placed = model.NewConstant(0)
                placed_vars.append(placed)
                rot_vars.append(None)
                x_starts.append((None, None))  # type: ignore
                y_starts.append((None, None))  # type: ignore
                pres_normal.append(model.NewConstant(0))
                pres_rotated.append(None)
                weights.append(p.priority * (p.width_mm * p.height_mm))
                continue

            placed = model.NewBoolVar(f"placed_{i}")
            placed_vars.append(placed)

            pn = model.NewBoolVar(f"pres_n_{i}") if fits_normal else model.NewConstant(0)
            pr = (
                model.NewBoolVar(f"pres_r_{i}")
                if fits_rotated
                else (model.NewConstant(0) if not fits_normal else None)
            )

            pres_normal.append(pn)
            pres_rotated.append(pr if fits_rotated else None)

            # placed == pn + pr
            if fits_rotated:
                model.Add(placed == pn + pr)
                # En fazla bir oryantasyon aktif (zaten placed<=1 garantiler)
            else:
                model.Add(placed == pn)

            if p.grain == GrainConstraint.PREFER_FIXED and fits_rotated:
                # Yumusak ceza: ek bir agirlik faktoru ekleyecegiz
                pass

            # Normal oryantasyon intervals
            xs_n = ys_n = None
            if fits_normal:
                xs_n = model.NewIntVar(
                    x_offset,
                    x_offset + usable_w - p.width_mm,
                    f"x_n_{i}",
                )
                ys_n = model.NewIntVar(
                    y_offset,
                    y_offset + usable_h - p.height_mm,
                    f"y_n_{i}",
                )
                xi_n = model.NewOptionalIntervalVar(
                    xs_n, p.width_mm + k, xs_n + p.width_mm + k, pn, f"xiv_n_{i}"
                )
                yi_n = model.NewOptionalIntervalVar(
                    ys_n, p.height_mm + k, ys_n + p.height_mm + k, pn, f"yiv_n_{i}"
                )
                x_intervals.append(xi_n)
                y_intervals.append(yi_n)

            xs_r = ys_r = None
            if fits_rotated:
                xs_r = model.NewIntVar(
                    x_offset,
                    x_offset + usable_w - p.height_mm,
                    f"x_r_{i}",
                )
                ys_r = model.NewIntVar(
                    y_offset,
                    y_offset + usable_h - p.width_mm,
                    f"y_r_{i}",
                )
                xi_r = model.NewOptionalIntervalVar(
                    xs_r, p.height_mm + k, xs_r + p.height_mm + k, pr, f"xiv_r_{i}"
                )
                yi_r = model.NewOptionalIntervalVar(
                    ys_r, p.width_mm + k, ys_r + p.width_mm + k, pr, f"yiv_r_{i}"
                )
                x_intervals.append(xi_r)
                y_intervals.append(yi_r)

            x_starts.append((xs_n, xs_r))
            y_starts.append((ys_n, ys_r))
            rot_vars.append(pr if fits_rotated else None)

            # Yerlesim agirligi: oncelik * alan (mm^2 fazla buyuk olunca
            # int taban hatasi olmasin diye 1000'e bolelim)
            weight = max(1, p.priority * (p.width_mm * p.height_mm) // 1000)
            weights.append(weight)

        # 2D ortusmeme kisiti - tum optional intervaller
        if x_intervals:
            model.AddNoOverlap2D(x_intervals, y_intervals)

        # Amac: agirlikli yerlesim toplami
        obj_terms = []
        for i, ep in enumerate(expanded):
            p = ep.base
            placed = placed_vars[i]
            obj_terms.append(weights[i] * placed)

            # PREFER_FIXED icin donmus oryantasyona kucuk ceza
            if (
                p.grain == GrainConstraint.PREFER_FIXED
                and pres_rotated[i] is not None
            ):
                penalty = max(1, weights[i] // 20)
                obj_terms.append(-penalty * pres_rotated[i])

        model.Maximize(sum(obj_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.settings.time_limit_s
        solver.parameters.num_search_workers = self.settings.num_workers
        solver.parameters.log_search_progress = self.settings.log_search_progress
        solver.parameters.random_seed = self.settings.random_seed

        status = solver.Solve(model)
        status_name = solver.StatusName(status)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return SheetSolution(stock=sheet), [], status_name

        placements: List[Placement] = []
        placed_ids: List[str] = []

        for i, ep in enumerate(expanded):
            if solver.Value(placed_vars[i]) != 1:
                continue
            p = ep.base
            pn = pres_normal[i]
            pr = pres_rotated[i]

            is_rotated = pr is not None and solver.Value(pr) == 1

            if is_rotated:
                x = solver.Value(x_starts[i][1])
                y = solver.Value(y_starts[i][1])
                w = p.height_mm
                h = p.width_mm
                orient = CutOrientation.ROTATED_90
            else:
                x = solver.Value(x_starts[i][0])
                y = solver.Value(y_starts[i][0])
                w = p.width_mm
                h = p.height_mm
                orient = CutOrientation.NORMAL

            placements.append(
                Placement(
                    part_id=ep.instance_id,
                    x_mm=x,
                    y_mm=y,
                    width_mm=w,
                    height_mm=h,
                    orientation=orient,
                )
            )
            placed_ids.append(ep.instance_id)

        return SheetSolution(stock=sheet, placements=placements), placed_ids, status_name
