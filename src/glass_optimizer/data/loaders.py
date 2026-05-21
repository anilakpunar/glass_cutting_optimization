"""Girdi dosyalarini yukleme katmani.

Desteklenen formatlar:
    - JSON   : tek dosyada hem stok hem siparis
    - CSV    : ayri ayri stok.csv ve parts.csv
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from ..domain.models import KerfSettings, PartOrder, StockSheet


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
                    allow_rotation=str(row.get("allow_rotation", "true")).lower()
                    in ("1", "true", "yes", "evet"),
                    grain=row.get("grain", "none"),
                    priority=int(row.get("priority", 1)),
                    customer=row.get("customer") or None,
                    notes=row.get("notes") or None,
                )
            )
    return parts
