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

    keys_in_stock = {s.match_key for s in stock}
    keys_in_parts = {p.match_key for p in parts}
    missing = keys_in_parts - keys_in_stock
    if missing:
        raise ValidationError(
            "Bu malzeme/cam tipleri icin stokta plaka yok: "
            + ", ".join(sorted(missing))
        )

    for part in parts:
        if not _fits_into_any_stock(part, stock, kerf):
            raise ValidationError(
                f"Parca '{part.part_id}' ({part.width_mm}x{part.height_mm}, "
                f"malzeme={part.match_key}) ayni malzemeden hicbir stok plakaya "
                "sigmiyor; kenar payi ve rotasyon kontrol edin."
            )

    _validate_breakage(parts, kerf)


def _validate_breakage(parts: List[PartOrder], kerf: KerfSettings) -> None:
    """Kirma masasi (breakout) kurallarini dogrular.

    Cam, kesildikten sonra masada kirilarak ayristirilir; cok kucuk ya da
    asiri ince-uzun parcalar kirma sirasinda catlar/dagilir.
    """
    errors: List[str] = []
    for p in parts:
        short = min(p.width_mm, p.height_mm)
        long = max(p.width_mm, p.height_mm)

        if kerf.min_part_mm and short < kerf.min_part_mm:
            errors.append(
                f"  '{p.part_id}' {p.width_mm}x{p.height_mm}: en kucuk kenar "
                f"{short} mm < min_part_mm ({kerf.min_part_mm} mm) - kirma "
                "masasinda guvenle elde edilemez."
            )
        if kerf.max_aspect_ratio and short > 0 and (long / short) > kerf.max_aspect_ratio:
            errors.append(
                f"  '{p.part_id}' {p.width_mm}x{p.height_mm}: en/boy orani "
                f"{long / short:.1f} > max_aspect_ratio ({kerf.max_aspect_ratio}) "
                "- kirma sirasinda esneyip catlayabilir."
            )

    if errors:
        raise ValidationError(
            "Kirma masasi kurallari ihlali:\n" + "\n".join(errors)
        )


def _fits_into_any_stock(
    part: PartOrder, stock: List[StockSheet], kerf: KerfSettings
) -> bool:
    margin = 2 * kerf.edge_trim_mm
    for s in stock:
        if s.match_key != part.match_key:
            continue
        usable_w = s.width_mm - margin
        usable_h = s.height_mm - margin
        if part.width_mm <= usable_w and part.height_mm <= usable_h:
            return True
        if part.allow_rotation and (
            part.height_mm <= usable_w and part.width_mm <= usable_h
        ):
            return True
    return False
