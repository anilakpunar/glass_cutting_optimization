"""sample_input.json'u kullanicinin gercek siparis verisinden uretir.

Ondalikli olculer (orn. 599.500 mm) mm tam sayisina yuvarlanir
(kerf >= toleranslar). Ayni urun adi (PLAKA TIPI) bir 'material' kodu
olur; ayni glass_type+kalinligi paylasan farkli urunler (Low-E TEC 15
ile EKO PRO gibi) boylece karismaz.

    python examples/build_sample_from_order.py
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path

# PLAKA TIPI | PLAKA EBAT | URUN EN | URUN BOY | URUN MIKTARI
RAW = """
DUZ CAM 4 MM	6000X3210	383.000	578.000	246
DUZ CAM 4 MM	6000X3210	320.000	433.000	83
DUZ CAM 4 MM	6000X3210	349.000	433.000	45
DUZ CAM 4 MM	6000X3210	320.000	433.000	396
DUZ CAM 4 MM	6000X3210	349.000	433.000	64
DUZ CAM 4 MM	6000X3210	373.000	488.000	48
DUZ CAM 4 MM	6000X3210	349.000	433.000	122
DUZ CAM 4 MM	6000X3210	373.000	488.000	624
SERT LOW-E TEC 15 4 MM	3302X2134	748.000	599.500	1064
SERT LOW-E TEC 15 4 MM	3302X2134	748.000	599.500	840
SERT LOW-E TEC 15 4 MM	3302X2134	748.000	567.100	518
SERT LOW-E TEC 15 4 MM	3302X2134	748.000	567.100	672
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	523.000	635.500	168
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	523.000	635.500	112
SERT LOW-E TEC 15 4 MM	3302X2134	533.000	826.000	130
SERT LOW-E TEC 15 4 MM	3302X2134	561.000	826.000	216
YUMUSAK LOW-E ENERJI 4 MM	6000X3210	373.000	488.000	416
DUZ CAM 4 MM	6000X3210	513.000	1.554.000	22
DUZ CAM 4 MM	3210X2250	569.000	1.505.000	63
SERT LOW-E TEC 15 4 MM	3302X2134	561.000	1.204.000	56
SERT LOW-E TEC 15 4 MM	3302X2134	836.500	573.500	98
SERT LOW-E TEC 15 4 MM	3302X2134	531.000	1.204.000	56
SERT LOW-E TEC 15 4 MM	3302X2134	836.500	573.500	7
SERT LOW-E EKO PRO CLEAR 4 MM	3210X2000	1.203.000	772.900	96
SERT LOW-E TEC 15 4 MM	3302X2134	836.500	573.500	12
DUZ CAM 4 MM	3210X2250	585.500	1.391.500	114
DUZ CAM 4 MM	3210X2250	677.000	820.000	38
DUZ CAM 4 MM	3210X2250	677.000	820.000	44
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	524.800	1.255.000	292
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	545.500	916.900	16
DUZ CAM 8 MM	3210X2250	643.300	1.181.400	35
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	394.700	916.900	34
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	704.200	1.255.000	6
SERT LOW-E EKO PRO CLEAR 4 MM	3210X2000	1.003.000	737.800	329
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	543.500	914.900	12
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	392.700	914.900	26
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	229.200	647.200	18
DUZ CAM 4 MM	3210X2000	513.000	1.554.000	12
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	704.200	1.255.000	54
YUMUSAK LOW-E ENERJI 3 MM	6000X3210	229.200	647.200	39
DUZ CAM FUME 4 MM	3210X2500	592.000	718.250	320
SERT LOW-E EKO PRO CLEAR 4 MM	3210X2000	1.203.000	772.900	372
SERT LOW-E EKO PRO CLEAR 4 MM	3210X2000	678.000	772.000	62
SERT LOW-E EKO PRO CLEAR 4 MM	3210X2000	878.000	737.800	152
DUZ CAM 4 MM	3210X2000	513.000	1.554.000	12
DUZ CAM 3 MM	3210X2250	704.200	1.491.500	60
DUZ CAM 3 MM	3210X2250	704.200	1.491.500	504
DUZ CAM 3 MM	3210X2250	615.300	1.255.000	28
DUZ CAM 3 MM	3210X2250	524.800	1.255.000	297
DUZ CAM 3 MM	3210X2250	545.500	916.900	33
"""

# Urun adi -> (material kodu, glass_type, kalinlik mm, birim maliyet)
PRODUCT = {
    "DUZ CAM 3 MM": ("DUZ_CAM_3MM", "float", 3.0, 1100.0),
    "DUZ CAM 4 MM": ("DUZ_CAM_4MM", "float", 4.0, 1500.0),
    "DUZ CAM 8 MM": ("DUZ_CAM_8MM", "float", 8.0, 2800.0),
    "DUZ CAM FUME 4 MM": ("DUZ_CAM_FUME_4MM", "float", 4.0, 1700.0),
    "SERT LOW-E TEC 15 4 MM": ("SERT_LOWE_TEC15_4MM", "low_e", 4.0, 1200.0),
    "SERT LOW-E EKO PRO CLEAR 4 MM": ("SERT_LOWE_EKOPRO_4MM", "low_e", 4.0, 1900.0),
    "YUMUSAK LOW-E ENERJI 3 MM": ("YUMUSAK_LOWE_ENERJI_3MM", "low_e", 3.0, 1300.0),
    "YUMUSAK LOW-E ENERJI 4 MM": ("YUMUSAK_LOWE_ENERJI_4MM", "low_e", 4.0, 1600.0),
}


def parse_mm(token: str) -> int:
    """ '599.500' -> 600 ; '1.554.000' -> 1554 (tum noktalar kaldirilir,
    deger 1000'e bolunur -> mm, sonra yukari/asagi en yakina yuvarlanir)."""
    digits = token.replace(".", "")
    value = int(digits) / 1000.0
    return int(math.floor(value + 0.5))


def parse_plate(token: str) -> tuple[int, int]:
    w, h = token.upper().split("X")
    return int(w), int(h)


def main() -> None:
    # parts[material][(w,h)] = qty toplami
    parts_qty: dict[str, dict[tuple[int, int], int]] = defaultdict(lambda: defaultdict(int))
    plates: dict[str, set[tuple[int, int]]] = defaultdict(set)
    meta: dict[str, tuple[str, float, float]] = {}  # material -> (glass_type, thk, cost)

    for line in RAW.strip().splitlines():
        cols = [c.strip() for c in line.split("\t")]
        if len(cols) != 5:
            cols = re.split(r"\t+|\s{2,}", line.strip())
        prod, plate, en, boy, qty = cols
        material, gtype, thk, cost = PRODUCT[prod]
        w = parse_mm(en)
        h = parse_mm(boy)
        pw, ph = parse_plate(plate)
        parts_qty[material][(w, h)] += int(qty)
        plates[material].add((pw, ph))
        meta[material] = (gtype, thk, cost)

    # Stok: her material icin gorulen plaka boyutlarini ekle, yeterli adetle
    stock = []
    parts = []
    for material in sorted(parts_qty):
        gtype, thk, cost = meta[material]
        total_area = sum(w * h * q for (w, h), q in parts_qty[material].items())

        for (pw, ph) in sorted(plates[material], key=lambda p: -p[0] * p[1]):
            plate_area = pw * ph
            # ~%62 doluluk varsayimi ile yeterli plaka (guillotine + kirma
            # kurallari fire payi dahil)
            qty = math.ceil(total_area / plate_area / 0.62) + 3
            stock.append({
                "sheet_id": f"{material}_{pw}x{ph}",
                "width_mm": pw,
                "height_mm": ph,
                "glass_type": gtype,
                "thickness_mm": thk,
                "material": material,
                "quantity": qty,
                "unit_cost": round(cost * plate_area / (6000 * 3210), 2) if False else cost,
            })

        for (w, h), q in sorted(parts_qty[material].items(), key=lambda kv: -kv[0][0] * kv[0][1]):
            parts.append({
                "part_id": f"{material}-{w}x{h}",
                "width_mm": w,
                "height_mm": h,
                "quantity": q,
                "glass_type": gtype,
                "thickness_mm": thk,
                "material": material,
                "allow_rotation": True,
                "priority": 5,
            })

    job = {
        "kerf": {"kerf_mm": 3, "edge_trim_mm": 10, "min_offcut_mm": 200},
        "stock": stock,
        "parts": parts,
    }

    out = Path(__file__).resolve().parent / "sample_input.json"
    out.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    n_parts = sum(p["quantity"] for p in parts)
    print(f"{len(stock)} stok tanimi, {len(parts)} parca kalemi, {n_parts} toplam parca")
    print(f"Malzemeler: {', '.join(sorted(parts_qty))}")
    print(f"Yazildi: {out}")


if __name__ == "__main__":
    main()
