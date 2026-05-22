"""Girdi dosyalarini yukleme katmani.

Desteklenen formatlar:
    - JSON   : tek dosyada hem stok hem siparis
    - CSV    : ayri ayri stok.csv ve parts.csv
    - Excel  : siparis tablosu (.xlsx) - urun adindan material/tip turetir
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from ..domain.models import KerfSettings, PartOrder, StockSheet
from .order_table import build_job_from_rows, rows_from_records


@dataclass
class Job:
    stock: List[StockSheet]
    parts: List[PartOrder]
    kerf: KerfSettings


def load_job_from_json(path: str | Path) -> Job:
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    kerf = KerfSettings(**data.get("kerf", {}))
    stock = [StockSheet(**s) for s in data.get("stock", [])]
    parts = [PartOrder(**p) for p in data.get("parts", [])]
    return Job(stock=stock, parts=parts, kerf=kerf)


def load_stock_from_csv(path: str | Path) -> List[StockSheet]:
    sheets: List[StockSheet] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sheets.append(
                StockSheet(
                    sheet_id=row["sheet_id"],
                    width_mm=int(row["width_mm"]),
                    height_mm=int(row["height_mm"]),
                    glass_type=row.get("glass_type", "float"),
                    thickness_mm=float(row.get("thickness_mm", 4.0)),
                    material=row.get("material") or None,
                    quantity=int(row.get("quantity", 1)),
                    unit_cost=float(row.get("unit_cost", 0.0)),
                )
            )
    return sheets


def load_parts_from_csv(path: str | Path) -> List[PartOrder]:
    parts: List[PartOrder] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            parts.append(
                PartOrder(
                    part_id=row["part_id"],
                    width_mm=int(row["width_mm"]),
                    height_mm=int(row["height_mm"]),
                    quantity=int(row.get("quantity", 1)),
                    glass_type=row.get("glass_type", "float"),
                    thickness_mm=float(row.get("thickness_mm", 4.0)),
                    material=row.get("material") or None,
                    allow_rotation=str(row.get("allow_rotation", "true")).lower()
                    in ("1", "true", "yes", "evet"),
                    grain=row.get("grain", "none"),
                    priority=int(row.get("priority", 1)),
                    customer=row.get("customer") or None,
                    notes=row.get("notes") or None,
                )
            )
    return parts


# Tipik kalinliga gore varsayilan plaka birim maliyeti (Excel'de fiyat yoksa)
_DEFAULT_COSTS = {3.0: 1100.0, 4.0: 1500.0, 6.0: 2200.0, 8.0: 2800.0, 10.0: 3500.0}


def load_order_table_from_excel(
    path: str | Path,
    *,
    sheet_name: int | str = 0,
    kerf: KerfSettings | None = None,
    fill_factor: float = 0.70,
) -> Job:
    """Siparis tablosu formatindaki Excel'i (.xlsx) okur ve Job uretir.

    Beklenen kolonlar (esnek isim eslestirme):
        PLAKA TIPI | PLAKA EBAT | URUN EN | URUN BOY | URUN MIKTARI
    Istege bagli: BIRIM MALIYET.
    """
    import pandas as pd

    df = pd.read_excel(path, sheet_name=sheet_name)
    if hasattr(df, "to_dict"):
        records = df.where(df.notna(), None).to_dict(orient="records")
    else:  # birden fazla sheet dondurulduyse ilkini al
        first = next(iter(df.values()))
        records = first.where(first.notna(), None).to_dict(orient="records")

    rows = rows_from_records(records)
    stock, parts = build_job_from_rows(
        rows, fill_factor=fill_factor, default_costs=_DEFAULT_COSTS
    )
    return Job(stock=stock, parts=parts, kerf=kerf or KerfSettings())


def load_order_table_from_records(
    records: List[dict],
    *,
    kerf: KerfSettings | None = None,
    fill_factor: float = 0.70,
) -> Job:
    """Order-table dict listesinden (orn. yuklenen df) Job uretir."""
    rows = rows_from_records(records)
    stock, parts = build_job_from_rows(
        rows, fill_factor=fill_factor, default_costs=_DEFAULT_COSTS
    )
    return Job(stock=stock, parts=parts, kerf=kerf or KerfSettings())
