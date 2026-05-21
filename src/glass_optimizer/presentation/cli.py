"""Komut satiri arayuzu (typer)."""

from __future__ import annotations

from pathlib import Path

import typer

from ..config.settings import OptimizerSettings
from ..data.loaders import load_job_from_json
from ..data.validators import validate_job
from ..optimization.multi_sheet import MultiSheetOrchestrator
from .reporter import print_console_report, write_text_report
from .visualizer import render_cutting_layouts


app = typer.Typer(
    help="Cam Kesim Optimizasyonu (OR-Tools CP-SAT)",
    no_args_is_help=True,
)


@app.command()
def optimize(
    job_file: Path = typer.Argument(
        ..., exists=True, help="JSON formatinda is dosyasi"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output", "-o", help="Cikti klasoru"
    ),
    time_limit: float = typer.Option(
        30.0, "--time-limit", "-t", help="Plaka basina cozucu suresi (s)"
    ),
    workers: int = typer.Option(
        8, "--workers", "-w", help="Paralel CP-SAT calisan sayisi"
    ),
    no_visual: bool = typer.Option(
        False, "--no-visual", help="Gorsel PNG uretimini atla"
    ),
) -> None:
    """Bir is dosyasini cozer ve raporlar uretir."""

    job = load_job_from_json(job_file)
    validate_job(job.stock, job.parts, job.kerf)

    settings = OptimizerSettings(time_limit_s=time_limit, num_workers=workers)
    orchestrator = MultiSheetOrchestrator(settings)
    result = orchestrator.solve(job.stock, job.parts, job.kerf)

    output_dir.mkdir(parents=True, exist_ok=True)
    print_console_report(result)
    write_text_report(result, output_dir / "report.txt")

    if not no_visual:
        files = render_cutting_layouts(result, output_dir)
        typer.echo(f"\n{len(files)} adet plaka gorseli uretildi: {output_dir}")


if __name__ == "__main__":
    app()
