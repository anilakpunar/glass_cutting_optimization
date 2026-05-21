"""Programatik kullanim ornegi.

    python examples/sample_run.py
"""

from pathlib import Path

from glass_optimizer.config.settings import OptimizerSettings
from glass_optimizer.data.loaders import load_job_from_json
from glass_optimizer.data.validators import validate_job
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator
from glass_optimizer.presentation.reporter import (
    print_console_report,
    write_text_report,
)
from glass_optimizer.presentation.visualizer import render_cutting_layouts


def main() -> None:
    here = Path(__file__).parent
    job = load_job_from_json(here / "sample_input.json")
    validate_job(job.stock, job.parts, job.kerf)

    settings = OptimizerSettings(
        strategy="hybrid",        # MaxRects + CP-SAT polish (en iyi kalite)
        time_limit_s=30.0,
        cpsat_polish_time_s=8.0,
        num_workers=8,
    )
    orchestrator = MultiSheetOrchestrator(settings)
    result = orchestrator.solve(job.stock, job.parts, job.kerf)

    out = here.parent / "output"
    out.mkdir(exist_ok=True)
    print_console_report(result)
    write_text_report(result, out / "report.txt")
    render_cutting_layouts(result, out)

    print(f"\nCikti: {out.resolve()}")


if __name__ == "__main__":
    main()
