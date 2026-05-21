"""Girdi dogrulamasi.

Cozumun mantiksiz girdi yuzunden patlamasini ya da yanlis cikti
uretmesini onlemek icin kullanilir.
"""

from __future__ import annotations

from typing import List

from ..domain.models import KerfSettings, PartOrder, StockSheet


class ValidationError(Exception):
    pass


def validate_job(
    stock: List[StockSheet],
    parts: List[PartOrder],
    kerf: KerfSettings,
) -> None:
    if not stock:
        raise ValidationError("En az bir stok plaka tanimlanmalidir.")
    if not parts:
        raise ValidationError("En az bir parca siparisi gereklidir.")

    for part in parts:
        if not _fits_into_any_stock(part, stock, kerf):
            raise ValidationError(
                f"Parca '{part.part_id}' ({part.width_mm}x{part.height_mm}) "
                "hicbir stok plakaya sigmiyor; kenar payi ve rotasyon kontrol edin."
            )

    types_in_parts = {p.glass_type for p in parts}
    types_in_stock = {s.glass_type for s in stock}
    missing = types_in_parts - types_in_stock
    if missing:
        raise ValidationError(
            f"Bu cam tipleri icin stokta plaka yok: {', '.join(t.value for t in missing)}"
        )


def _fits_into_any_stock(
    part: PartOrder, stock: List[StockSheet], kerf: KerfSettings
) -> bool:
    margin = 2 * kerf.edge_trim_mm
    for s in stock:
        usable_w = s.width_mm - margin
        usable_h = s.height_mm - margin
        if part.width_mm <= usable_w and part.height_mm <= usable_h:
            return True
        if part.allow_rotation and (
            part.height_mm <= usable_w and part.width_mm <= usable_h
        ):
            return True
    return False
