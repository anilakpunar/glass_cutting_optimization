"""Konsol ve dosya raporlamasi."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..domain.models import OptimizationResult
from ..services.cost_calculator import calculate_cost
from ..services.cutting_plan import build_cutting_plan
from ..services.waste_analyzer import analyze_waste


def print_console_report(result: OptimizationResult) -> None:
    console = Console()

    summary = Table(title="Optimizasyon Ozeti", show_header=False, box=None)
    summary.add_column(style="cyan", no_wrap=True)
    summary.add_column(style="bold")
    summary.add_row("Kullanilan plaka", str(result.sheets_used))
    summary.add_row("Toplam yerlesen alan (m²)", f"{result.total_used_area_mm2 / 1_000_000:.3f}")
    summary.add_row("Toplam fire (m²)", f"{result.total_waste_area_mm2 / 1_000_000:.3f}")
    summary.add_row("Genel verim", f"%{result.overall_utilization * 100:.2f}")
    summary.add_row("Cozucu durumu", result.solver_status)
    summary.add_row("Sure (s)", f"{result.total_runtime_s:.2f}")
    console.print(Panel(summary, title="Sonuc", border_style="green"))

    # Maliyet
    cost = calculate_cost(result)
    cost_t = Table(title="Maliyet Raporu")
    cost_t.add_column("Metrik")
    cost_t.add_column("Deger", justify="right")
    cost_t.add_row("Hammadde maliyeti", f"{cost.raw_material_cost:.2f}")
    cost_t.add_row("Kullanilan m²", f"{cost.used_area_m2:.3f}")
    cost_t.add_row("Fire m²", f"{cost.waste_area_m2:.3f}")
    cost_t.add_row("Fire degeri", f"{cost.waste_value:.2f}")
    cost_t.add_row("Birim m² maliyet (gercek)", f"{cost.cost_per_used_m2:.2f}")
    cost_t.add_row("Yerlesemeyen parca", str(cost.unplaced_count))
    console.print(cost_t)

    # Plaka basina
    sheets_t = Table(title="Plaka Detaylari")
    sheets_t.add_column("#")
    sheets_t.add_column("Plaka")
    sheets_t.add_column("Boyut")
    sheets_t.add_column("Cam Tipi")
    sheets_t.add_column("Parca", justify="right")
    sheets_t.add_column("Verim", justify="right")
    for i, s in enumerate(result.sheets, start=1):
        sheets_t.add_row(
            str(i),
            s.stock.sheet_id,
            f"{s.stock.width_mm}x{s.stock.height_mm}",
            s.stock.glass_type.value,
            str(len(s.placements)),
            f"%{s.utilization * 100:.1f}",
        )
    console.print(sheets_t)

    # Fire analizi
    waste = analyze_waste(result, result.kerf)
    if waste.reusable_offcuts:
        oc_t = Table(title="Yeniden Kullanilabilir Fireler (offcut)")
        oc_t.add_column("Plaka")
        oc_t.add_column("Konum (x,y)")
        oc_t.add_column("Boyut")
        oc_t.add_column("Alan m²", justify="right")
        for oc in waste.reusable_offcuts:
            oc_t.add_row(
                oc.sheet_id,
                f"({oc.x_mm},{oc.y_mm})",
                f"{oc.width_mm}x{oc.height_mm}",
                f"{oc.area_m2:.3f}",
            )
        console.print(oc_t)
        console.print(
            f"[bold green]Toplam geri kazanim potansiyeli:[/] "
            f"{waste.reusable_offcut_m2:.3f} m²"
        )

    if result.unplaced_parts:
        up_t = Table(title="Yerlesemeyen Siparisler", border_style="red")
        up_t.add_column("Parca ID")
        up_t.add_column("Boyut")
        up_t.add_column("Kalan adet", justify="right")
        up_t.add_column("Cam tipi")
        for p in result.unplaced_parts:
            up_t.add_row(
                p.part_id,
                f"{p.width_mm}x{p.height_mm}",
                str(p.quantity),
                p.glass_type.value,
            )
        console.print(up_t)


def write_text_report(result: OptimizationResult, path: str | Path) -> Path:
    cost = calculate_cost(result)
    waste = analyze_waste(result, result.kerf)
    plan = build_cutting_plan(result)

    lines = []
    lines.append("=" * 70)
    lines.append("CAM KESIM OPTIMIZASYON RAPORU")
    lines.append("=" * 70)
    lines.append(f"Cozucu durumu       : {result.solver_status}")
    lines.append(f"Calisma suresi      : {result.total_runtime_s:.2f} s")
    lines.append(f"Kullanilan plaka    : {result.sheets_used}")
    lines.append(
        f"Toplam stok alan    : {result.total_stock_area_mm2 / 1_000_000:.3f} m²"
    )
    lines.append(
        f"Toplam yerlesen alan: {result.total_used_area_mm2 / 1_000_000:.3f} m²"
    )
    lines.append(f"Toplam fire         : {result.total_waste_area_mm2 / 1_000_000:.3f} m²")
    lines.append(f"Genel verim         : %{result.overall_utilization * 100:.2f}")
    lines.append("")
    lines.append("-- Maliyet --")
    lines.append(f"Hammadde            : {cost.raw_material_cost:.2f}")
    lines.append(f"Fire degeri         : {cost.waste_value:.2f}")
    lines.append(f"Birim m² (gercek)   : {cost.cost_per_used_m2:.2f}")
    lines.append(f"Yerlesemeyen parca  : {cost.unplaced_count}")
    lines.append("")

    for sp in plan.sheet_plans:
        lines.append("-" * 70)
        lines.append(f"Plaka: {sp.sheet_id}")
        lines.append("-" * 70)
        for inst in sp.instructions:
            lines.append(
                f"  {inst.step:>3}. {inst.part_id:<20} {inst.description}"
            )
        lines.append("")

    if waste.reusable_offcuts:
        lines.append("-- Yeniden Kullanilabilir Fireler --")
        for oc in waste.reusable_offcuts:
            lines.append(
                f"  {oc.sheet_id}: ({oc.x_mm},{oc.y_mm}) "
                f"{oc.width_mm}x{oc.height_mm} = {oc.area_m2:.3f} m²"
            )
        lines.append(f"Toplam: {waste.reusable_offcut_m2:.3f} m²")
        lines.append("")

    if result.unplaced_parts:
        lines.append("-- Yerlesemeyen Siparisler --")
        for p in result.unplaced_parts:
            lines.append(
                f"  {p.part_id}: {p.width_mm}x{p.height_mm} "
                f"adet={p.quantity} tip={p.glass_type.value}"
            )

    out = Path(path)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out
