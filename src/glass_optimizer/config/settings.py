"""Optimizasyon calistirma ayarlari."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OptimizerSettings(BaseModel):
    time_limit_s: float = Field(default=30.0, gt=0)
    num_workers: int = Field(default=8, ge=1)
    enforce_guillotine: bool = Field(
        default=True,
        description="Endustriyel cam kesimde standart olan giyotin (uctan uca) kesim kisitlamasi",
    )
    allow_rotation_global: bool = True
    objective: str = Field(
        default="minimize_waste",
        description="minimize_waste | minimize_sheets | maximize_value",
    )
    log_search_progress: bool = False
    random_seed: int = 42

    # Olcekleme: yuksek parca sayilarinda CP-SAT'in bos vermemesi icin
    # her plaka cozumune giden aday parca havuzu kisitlanir.
    max_parts_per_sheet: int = Field(
        default=120,
        ge=8,
        description="Tek bir plaka CP-SAT modeline gonderilen maks. parca ornegi sayisi",
    )
    candidate_area_factor: float = Field(
        default=1.3,
        gt=1.0,
        description="Aday parca alanlari toplaminin, plaka alanina oranla ust siniri",
    )


def default_settings() -> OptimizerSettings:
    return OptimizerSettings()
