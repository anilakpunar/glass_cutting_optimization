"""CP-SAT tabanli tek plaka 2D yerlestirme cozucusu.

Model ozeti
-----------
Verilen tek bir stok plakasi ve bir parca havuzu uzerinden, hangi
parcalarin yerlestirilecegi ve nereye konacagi tam sayi degiskenleri
ile aranir.

Her parca icin:
  - placed     : Bool, yerlestirildi mi?
  - pres_n/r   : Bool, normal/donmus yerlesimde mi?
  - x_start    : Int, sol kenar (mm)
  - y_start    : Int, alt kenar (mm)

Kisitlar:
  - placed = pres_n + pres_r (0 veya 1)
  - Optional intervals + AddNoOverlap2D
  - Kerf parca olculerine eklenir (testere kalinligi guvenligi)

Warm-start (hints)
------------------
solve_single_sheet onceden uretilmis bir cozumu (genelde MaxRects)
`hints` parametresi ile alabilir. AddHint cagrilari sayesinde CP-SAT
arama isteklenen noktadan baslar; ayni surede daha yuksek verim
yakalanir.

Olcekleme
---------
Cok buyuk parca havuzlarinda CP-SAT bos verecegi icin, modele
gonderilen parca sayisi `settings.max_parts_per_sheet` ile sinirlanir
(oncelik DESC, alan DESC ile siralanmis ilk N).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

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
from .base import SheetSolver


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


def _cap_for_cpsat(
    expanded: List[_ExpandedPart],
    sheet: StockSheet,
    max_count: int,
    area_factor: float,
) -> List[_ExpandedPart]:
    """CP-SAT'in bogulmamasi icin top-K aday parca sec.

    Oncelik DESC, sonra alan DESC siralanir; toplam aday alani sheet alani x
    `area_factor` esiginde tutulur, en fazla `max_count` parca alinir.
    """
    if not expanded:
        return expanded
    if len(expanded) <= max_count:
        # Yine de alana gore koparak hizlandirabiliriz, fakat aday sayisi
        # zaten azsa olduiu gibi birak
        sorted_e = sorted(
            expanded,
            key=lambda e: (-e.base.priority, -(e.base.width_mm * e.base.height_mm)),
        )
        return sorted_e

    sorted_e = sorted(
        expanded,
        key=lambda e: (-e.base.priority, -(e.base.width_mm * e.base.height_mm)),
    )
    area_budget = int(sheet.area_mm2 * area_factor)
    total_area = 0
    result: List[_ExpandedPart] = []
    for e in sorted_e:
        if len(result) >= max_count:
            break
        a = e.base.width_mm * e.base.height_mm
        if total_area + a > area_budget:
            continue
        result.append(e)
        total_area += a
    return result


@dataclass
class _InstanceVars:
    placed: cp_model.IntVar
    pres_n: Optional[cp_model.IntVar]
    pres_r: Optional[cp_model.IntVar]
    xs_n: Optional[cp_model.IntVar]
    ys_n: Optional[cp_model.IntVar]
    xs_r: Optional[cp_model.IntVar]
    ys_r: Optional[cp_model.IntVar]


class CPSATSheetSolver(SheetSolver):
    """Tek bir plaka uzerinde maksimum yerlestirme yapan CP-SAT cozucu."""

    def solve_single_sheet(
        self,
        sheet: StockSheet,
        parts: List[PartOrder],
        kerf: KerfSettings,
        hints: Optional[List[Placement]] = None,
    ) -> Tuple[SheetSolution, List[str], str]:
        """Tek plaka icin cozum uretir.

        Parameters
        ----------
        hints : optional, MaxRects gibi onceki cozumden gelen yerlesim
                Placement listesi. instance_id eslesmesi ile CP-SAT
                degiskenlerine AddHint uygulanir.

        Returns
        -------
        (cozum, yerlesen parca instance_id listesi, solver_status)
        """

        expanded_all = _expand(parts)
        if not expanded_all:
            return SheetSolution(stock=sheet), [], "EMPTY"

        # Olcekleme: CP-SAT'a sadece top-K parca gonder
        expanded = _cap_for_cpsat(
            expanded_all,
            sheet,
            self.settings.max_parts_per_sheet,
            self.settings.candidate_area_factor,
        )

        usable_w = sheet.width_mm - 2 * kerf.edge_trim_mm
        usable_h = sheet.height_mm - 2 * kerf.edge_trim_mm
        x_offset = kerf.edge_trim_mm
        y_offset = kerf.edge_trim_mm
        k = kerf.kerf_mm

        model = cp_model.CpModel()

        x_intervals: List[cp_model.IntervalVar] = []
        y_intervals: List[cp_model.IntervalVar] = []

        instance_vars: Dict[str, _InstanceVars] = {}
        placed_vars: List[cp_model.IntVar] = []
        weights: List[int] = []

        for i, ep in enumerate(expanded):
            p = ep.base
            fits_normal = p.width_mm <= usable_w and p.height_mm <= usable_h
            fits_rotated = (
                p.allow_rotation
                and p.grain != GrainConstraint.FIXED
                and p.height_mm <= usable_w
                and p.width_mm <= usable_h
            )

            if not fits_normal and not fits_rotated:
                placed = model.NewConstant(0)
                placed_vars.append(placed)
                weights.append(p.priority * (p.width_mm * p.height_mm))
                instance_vars[ep.instance_id] = _InstanceVars(
                    placed=placed,
                    pres_n=None, pres_r=None,
                    xs_n=None, ys_n=None, xs_r=None, ys_r=None,
                )
                continue

            placed = model.NewBoolVar(f"placed_{i}")
            placed_vars.append(placed)

            pn = (
                model.NewBoolVar(f"pres_n_{i}") if fits_normal else None
            )
            pr = (
                model.NewBoolVar(f"pres_r_{i}") if fits_rotated else None
            )

            if pn is not None and pr is not None:
                model.Add(placed == pn + pr)
            elif pn is not None:
                model.Add(placed == pn)
            elif pr is not None:
                model.Add(placed == pr)

            xs_n = ys_n = None
            if pn is not None:
                xs_n = model.NewIntVar(
                    x_offset, x_offset + usable_w - p.width_mm, f"x_n_{i}"
                )
                ys_n = model.NewIntVar(
                    y_offset, y_offset + usable_h - p.height_mm, f"y_n_{i}"
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
            if pr is not None:
                xs_r = model.NewIntVar(
                    x_offset, x_offset + usable_w - p.height_mm, f"x_r_{i}"
                )
                ys_r = model.NewIntVar(
                    y_offset, y_offset + usable_h - p.width_mm, f"y_r_{i}"
                )
                xi_r = model.NewOptionalIntervalVar(
                    xs_r, p.height_mm + k, xs_r + p.height_mm + k, pr, f"xiv_r_{i}"
                )
                yi_r = model.NewOptionalIntervalVar(
                    ys_r, p.width_mm + k, ys_r + p.width_mm + k, pr, f"yiv_r_{i}"
                )
                x_intervals.append(xi_r)
                y_intervals.append(yi_r)

            weight = max(1, p.priority * (p.width_mm * p.height_mm) // 1000)
            weights.append(weight)
            instance_vars[ep.instance_id] = _InstanceVars(
                placed=placed,
                pres_n=pn, pres_r=pr,
                xs_n=xs_n, ys_n=ys_n, xs_r=xs_r, ys_r=ys_r,
            )

        if x_intervals:
            model.AddNoOverlap2D(x_intervals, y_intervals)

        # Amac
        obj_terms = []
        for i, ep in enumerate(expanded):
            obj_terms.append(weights[i] * placed_vars[i])
            iv = instance_vars[ep.instance_id]
            if (
                ep.base.grain == GrainConstraint.PREFER_FIXED
                and iv.pres_r is not None
            ):
                penalty = max(1, weights[i] // 20)
                obj_terms.append(-penalty * iv.pres_r)
        model.Maximize(sum(obj_terms))

        # Warm start: hints uygula
        if hints:
            self._apply_hints(model, instance_vars, hints)

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
        for ep in expanded:
            iv = instance_vars[ep.instance_id]
            if solver.Value(iv.placed) != 1:
                continue
            p = ep.base
            is_rotated = iv.pres_r is not None and solver.Value(iv.pres_r) == 1
            if is_rotated:
                x = solver.Value(iv.xs_r)
                y = solver.Value(iv.ys_r)
                w, h = p.height_mm, p.width_mm
                orient = CutOrientation.ROTATED_90
            else:
                x = solver.Value(iv.xs_n)
                y = solver.Value(iv.ys_n)
                w, h = p.width_mm, p.height_mm
                orient = CutOrientation.NORMAL

            placements.append(
                Placement(
                    part_id=ep.instance_id,
                    x_mm=x, y_mm=y,
                    width_mm=w, height_mm=h,
                    orientation=orient,
                )
            )
            placed_ids.append(ep.instance_id)

        return (
            SheetSolution(stock=sheet, placements=placements),
            placed_ids,
            status_name,
        )

    @staticmethod
    def _apply_hints(
        model: cp_model.CpModel,
        instance_vars: Dict[str, _InstanceVars],
        hints: List[Placement],
    ) -> None:
        """MaxRects vb. cozumden gelen yerlesimleri CP-SAT'e ipucu olarak ver."""
        for h in hints:
            iv = instance_vars.get(h.part_id)
            if iv is None:
                continue
            # Bool/IntVar olmayanlara (NewConstant) AddHint cagirmak guvensiz
            if not isinstance(iv.placed, cp_model.IntVar):
                continue
            model.AddHint(iv.placed, 1)

            is_rotated = h.orientation == CutOrientation.ROTATED_90
            if is_rotated and iv.pres_r is not None:
                model.AddHint(iv.pres_r, 1)
                if iv.pres_n is not None:
                    model.AddHint(iv.pres_n, 0)
                if iv.xs_r is not None:
                    model.AddHint(iv.xs_r, h.x_mm)
                if iv.ys_r is not None:
                    model.AddHint(iv.ys_r, h.y_mm)
            elif not is_rotated and iv.pres_n is not None:
                model.AddHint(iv.pres_n, 1)
                if iv.pres_r is not None:
                    model.AddHint(iv.pres_r, 0)
                if iv.xs_n is not None:
                    model.AddHint(iv.xs_n, h.x_mm)
                if iv.ys_n is not None:
                    model.AddHint(iv.ys_n, h.y_mm)
