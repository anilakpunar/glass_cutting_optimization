"""Siparis tablosu (order-table) cozumleyici.

Atolyelerin yaygin kullandigi su formattaki veriyi okur ve optimizasyon
modellerine (StockSheet + PartOrder) donusturur:

    PLAKA TIPI | PLAKA EBAT | URUN EN | URUN BOY | URUN MIKTARI
    DUZ CAM 4 MM | 6000X3210 | 383.000 | 578.000 | 246
    ...

Her benzersiz "PLAKA TIPI" bir `material` kodu olur; glass_type ve
kalinlik urun adindan cikarilir. Boylece ayni cam tipi+kalinligi
paylasan farkli urunler (Low-E TEC 15 vs EKO PRO) karismaz.

Ondalikli olculer (599.500, 1.554.000) mm tam sayisina yuvarlanir.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from ..domain.enums import GlassType
from ..domain.models import KerfSettings, PartOrder, StockSheet

# Esnek kolon adi eslestirme (kucuk harf, bosluksuz)
_COLS = {
    "product": ["plakatipi", "urun", "malzeme", "cam", "tip", "producttype"],
    "plate": ["plakaebat", "ebat", "plaka", "sheet", "platesize"],
    "width": ["urunen", "en", "genislik", "width", "w"],
    "height": ["urunboy", "boy", "yukseklik", "height", "h"],
    "qty": ["urunmiktari", "miktar", "adet", "quantity", "qty", "miktari"],
    "unit_cost": ["birimmaliyet", "maliyet", "fiyat", "cost", "unitcost"],
}

_TR_MAP = str.maketrans("İıŞşĞğÜüÖöÇç", "IiSsGgUuOoCc")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).translate(_TR_MAP).lower())


def material_code(name: str) -> str:
    """Urun adindan tutarli bir malzeme kodu uretir."""
    up = str(name).translate(_TR_MAP).upper().strip()
    up = up.replace("-", " ")
    code = re.sub(r"[^A-Z0-9]+", "_", up).strip("_")
    return code


def infer_glass_type(name: str) -> GlassType:
    n = str(name).translate(_TR_MAP).lower()
    if "low" in n and "e" in n:  # low-e / lowe
        return GlassType.LOW_E
    if "ayna" in n or "mirror" in n:
        return GlassType.MIRROR
    if "lamine" in n or "lamina" in n:
        return GlassType.LAMINATED
    if "temper" in n:
        return GlassType.TEMPERED
    if "desen" in n or "patterned" in n:
        return GlassType.PATTERNED
    return GlassType.FLOAT


def infer_thickness(name: str) -> float:
    """Urun adindaki son '<n> MM' degerini kalinlik olarak alir."""
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*mm", str(name).lower())
    if matches:
        return float(matches[-1].replace(",", "."))
    return 4.0


def parse_mm(token) -> int:
    """Olcuyu mm tam sayisina cevirir.

    - Sayisal girdi: dogrudan mm kabul edilir (599.5 -> 600).
    - Metin Avrupa formati: '599.500' -> 599.5 -> 600; '1.554.000' -> 1554.
      (Tum gruplama noktalari kaldirilip 1000'e bolunur; veride olculer
      daima 3 ondalik haneyle gelir.)
    """
    if token is None:
        raise ValueError("Bos olcu")
    if isinstance(token, bool):
        raise ValueError("Gecersiz olcu")
    if isinstance(token, (int, float)):
        return int(math.floor(float(token) + 0.5))
    s = str(token).strip().replace(" ", "")
    if not s:
        raise ValueError("Bos olcu")
    if s.count(".") >= 2 or "," in s:
        digits = s.replace(".", "").replace(",", "")
        return int(math.floor(int(digits) / 1000 + 0.5))
    return int(math.floor(float(s) + 0.5))


def parse_plate(token) -> Tuple[int, int]:
    s = str(token).translate(_TR_MAP).upper().replace(" ", "")
    parts = re.split(r"[X*]", s)
    if len(parts) != 2:
        raise ValueError(f"Plaka ebati cozulemedi: {token!r} (orn. 6000X3210)")
    return int(float(parts[0])), int(float(parts[1]))


@dataclass
class OrderRow:
    product: str
    plate_w: int
    plate_h: int
    width: int
    height: int
    qty: int
    unit_cost: Optional[float] = None


def build_job_from_rows(
    rows: Sequence[OrderRow],
    *,
    fill_factor: float = 0.70,
    default_costs: Optional[Dict[float, float]] = None,
) -> Tuple[List[StockSheet], List[PartOrder]]:
    """Order satirlarindan stock + parts uretir.

    Ayni (material, en, boy) satirlari toplanir. Her material icin gorulen
    plaka boyutlari stok olarak eklenir; adet, ~fill_factor doluluk
    varsayimiyla tum parcalari karsilayacak kadar verilir.
    """
    if not rows:
        return [], []

    parts_qty: Dict[str, Dict[Tuple[int, int], int]] = defaultdict(lambda: defaultdict(int))
    plates: Dict[str, set] = defaultdict(set)
    meta: Dict[str, Tuple[GlassType, float, Optional[float]]] = {}

    for r in rows:
        mat = material_code(r.product)
        parts_qty[mat][(r.width, r.height)] += int(r.qty)
        plates[mat].add((r.plate_w, r.plate_h))
        gtype = infer_glass_type(r.product)
        thk = infer_thickness(r.product)
        prev_cost = meta.get(mat, (None, None, None))[2]
        cost = r.unit_cost if r.unit_cost is not None else prev_cost
        meta[mat] = (gtype, thk, cost)

    stock: List[StockSheet] = []
    parts: List[PartOrder] = []

    for mat in sorted(parts_qty):
        gtype, thk, cost = meta[mat]
        if cost is None and default_costs:
            cost = default_costs.get(thk, 0.0)
        cost = cost or 0.0
        total_area = sum(w * h * q for (w, h), q in parts_qty[mat].items())

        for (pw, ph) in sorted(plates[mat], key=lambda p: -p[0] * p[1]):
            qty = math.ceil(total_area / (pw * ph) / max(0.1, fill_factor)) + 3
            stock.append(
                StockSheet(
                    sheet_id=f"{mat}_{pw}x{ph}",
                    width_mm=pw, height_mm=ph,
                    glass_type=gtype, thickness_mm=thk,
                    material=mat, quantity=qty, unit_cost=cost,
                )
            )

        for (w, h), q in sorted(parts_qty[mat].items(), key=lambda kv: -kv[0][0] * kv[0][1]):
            parts.append(
                PartOrder(
                    part_id=f"{mat}-{w}x{h}",
                    width_mm=w, height_mm=h, quantity=q,
                    glass_type=gtype, thickness_mm=thk,
                    material=mat, allow_rotation=True, priority=5,
                )
            )

    return stock, parts


def rows_from_records(records: Sequence[dict]) -> List[OrderRow]:
    """Esnek kolon adli dict listesini OrderRow listesine cevirir."""
    if not records:
        return []

    # Kolon adi -> normalize edilmis isim eslemesi (ilk kayda gore)
    sample_keys = list(records[0].keys())
    norm_to_key = {_norm(k): k for k in sample_keys}

    def find(field: str) -> Optional[str]:
        for alias in _COLS[field]:
            if alias in norm_to_key:
                return norm_to_key[alias]
        # kismi eslesme
        for nk, orig in norm_to_key.items():
            if any(alias in nk for alias in _COLS[field]):
                return orig
        return None

    col = {f: find(f) for f in _COLS}
    missing = [f for f in ("product", "plate", "width", "height", "qty") if not col[f]]
    if missing:
        raise ValueError(
            "Excel kolonlari eslesmedi. Gerekli: PLAKA TIPI, PLAKA EBAT, "
            f"URUN EN, URUN BOY, URUN MIKTARI. Eksik: {missing}. "
            f"Bulunan kolonlar: {sample_keys}"
        )

    rows: List[OrderRow] = []
    for rec in records:
        product = rec.get(col["product"])
        plate = rec.get(col["plate"])
        if product is None or plate is None or str(product).strip() == "":
            continue
        pw, ph = parse_plate(plate)
        unit_cost = None
        if col["unit_cost"] and rec.get(col["unit_cost"]) not in (None, ""):
            try:
                unit_cost = float(str(rec[col["unit_cost"]]).replace(",", "."))
            except ValueError:
                unit_cost = None
        rows.append(
            OrderRow(
                product=str(product).strip(),
                plate_w=pw, plate_h=ph,
                width=parse_mm(rec[col["width"]]),
                height=parse_mm(rec[col["height"]]),
                qty=int(float(rec[col["qty"]])),
                unit_cost=unit_cost,
            )
        )
    return rows
