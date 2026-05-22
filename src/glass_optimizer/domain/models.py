"""Domain modelleri.

Tum olculer milimetre (mm) cinsinden tam sayi olarak tutulur; bu
CP-SAT'in tam sayi araligi ile birebir uyumludur ve floating-point
yuvarlama hatalarini onler.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .enums import GlassType, GrainConstraint, CutOrientation


class KerfSettings(BaseModel):
    """Testere / kesici kalinligi, guvenlik paylari ve kirma kurallari."""

    kerf_mm: int = Field(default=3, ge=0, description="Kesim sirasinda kaybedilen mm")
    edge_trim_mm: int = Field(
        default=10, ge=0, description="Plaka kenarindan kesilen guvenlik payi"
    )
    min_offcut_mm: int = Field(
        default=100,
        ge=0,
        description="Bu degerin altindaki fire parcalari yeniden kullanilamaz sayilir",
    )

    # --- Kirma masasi (breakout) kurallari: cam catlamasini onler ---
    min_part_mm: int = Field(
        default=50,
        ge=0,
        description=(
            "Kirma masasinda guvenle koparilabilen/elde edilebilen en kucuk "
            "parca kenari. Daha kucuk parcalar reddedilir (0 = kural kapali)."
        ),
    )
    max_aspect_ratio: float = Field(
        default=12.0,
        ge=0,
        description=(
            "Parca uzun/kisa kenar orani ust siniri. Asiri ince-uzun parcalar "
            "kirma sirasinda esneyip catlar (ozellikle ince cam). 0 = kapali."
        ),
    )
    min_break_strip_mm: int = Field(
        default=50,
        ge=0,
        description=(
            "Kirma masasinda temiz koparilabilen en ince serit. Bir kesimin "
            "yaninda bundan ince serit birakilirsa o cizgi temiz kirilamaz; "
            "cozucu boyle ince serit olusturmaz, bu bolgeyi fire birakir "
            "(0 = kural kapali)."
        ),
    )


class StockSheet(BaseModel):
    """Stoktaki ham cam plakasi."""

    sheet_id: str
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    glass_type: GlassType = GlassType.FLOAT
    thickness_mm: float = Field(default=4.0, gt=0)
    material: Optional[str] = Field(
        default=None,
        description=(
            "Urun/malzeme kodu. Ayni glass_type+kalinligi paylasan fakat "
            "birbirine donusturulemeyen urunleri ayirir (orn. Low-E TEC 15 "
            "ile EKO PRO). Verildiyse eslestirme anahtari budur."
        ),
    )
    quantity: int = Field(default=1, ge=1, description="Stoktaki adet")
    unit_cost: float = Field(default=0.0, ge=0, description="Plaka birim maliyeti")

    @property
    def area_mm2(self) -> int:
        return self.width_mm * self.height_mm

    @property
    def match_key(self) -> str:
        """Parca-stok eslestirme anahtari."""
        if self.material:
            return self.material
        return f"{self.glass_type.value}|{self.thickness_mm}"


class PartOrder(BaseModel):
    """Musteri siparisi: bir veya birden fazla ayni boyutta parca."""

    part_id: str
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)
    glass_type: GlassType = GlassType.FLOAT
    thickness_mm: float = Field(default=4.0, gt=0)
    material: Optional[str] = Field(
        default=None,
        description="Urun/malzeme kodu (StockSheet.material ile eslesir).",
    )
    allow_rotation: bool = True
    grain: GrainConstraint = GrainConstraint.NONE
    priority: int = Field(
        default=1, ge=1, le=10, description="1=dusuk, 10=kritik (acil siparis)"
    )
    customer: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _enforce_grain_rotation(self) -> "PartOrder":
        if self.grain == GrainConstraint.FIXED and self.allow_rotation:
            object.__setattr__(self, "allow_rotation", False)
        return self

    @property
    def area_mm2(self) -> int:
        return self.width_mm * self.height_mm

    @property
    def match_key(self) -> str:
        """Parca-stok eslestirme anahtari."""
        if self.material:
            return self.material
        return f"{self.glass_type.value}|{self.thickness_mm}"


class Placement(BaseModel):
    """Bir parcanin plaka uzerindeki nihai konumu."""

    part_id: str
    x_mm: int
    y_mm: int
    width_mm: int
    height_mm: int
    orientation: CutOrientation = CutOrientation.NORMAL

    @property
    def x2_mm(self) -> int:
        return self.x_mm + self.width_mm

    @property
    def y2_mm(self) -> int:
        return self.y_mm + self.height_mm

    @property
    def area_mm2(self) -> int:
        return self.width_mm * self.height_mm


class SheetSolution(BaseModel):
    """Tek bir stok plakasi uzerindeki yerlesim cozumu."""

    stock: StockSheet
    placements: List[Placement] = Field(default_factory=list)

    @property
    def used_area_mm2(self) -> int:
        return sum(p.area_mm2 for p in self.placements)

    @property
    def waste_area_mm2(self) -> int:
        return max(0, self.stock.area_mm2 - self.used_area_mm2)

    @property
    def utilization(self) -> float:
        if self.stock.area_mm2 == 0:
            return 0.0
        return self.used_area_mm2 / self.stock.area_mm2


class OptimizationResult(BaseModel):
    """Tum optimizasyon ciktisi."""

    sheets: List[SheetSolution] = Field(default_factory=list)
    unplaced_parts: List[PartOrder] = Field(default_factory=list)
    total_runtime_s: float = 0.0
    solver_status: str = "UNKNOWN"
    kerf: KerfSettings = Field(default_factory=KerfSettings)

    @property
    def total_used_area_mm2(self) -> int:
        return sum(s.used_area_mm2 for s in self.sheets)

    @property
    def total_stock_area_mm2(self) -> int:
        return sum(s.stock.area_mm2 for s in self.sheets)

    @property
    def total_waste_area_mm2(self) -> int:
        return self.total_stock_area_mm2 - self.total_used_area_mm2

    @property
    def overall_utilization(self) -> float:
        if self.total_stock_area_mm2 == 0:
            return 0.0
        return self.total_used_area_mm2 / self.total_stock_area_mm2

    @property
    def sheets_used(self) -> int:
        return len([s for s in self.sheets if s.placements])
