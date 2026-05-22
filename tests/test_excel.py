"""Excel / order-table girdi testleri."""

from __future__ import annotations

import pandas as pd
import pytest

from glass_optimizer.data.loaders import (
    load_order_table_from_excel,
    load_order_table_from_records,
)
from glass_optimizer.data.order_table import (
    infer_glass_type,
    infer_thickness,
    material_code,
    parse_mm,
    parse_plate,
)
from glass_optimizer.data.validators import validate_job
from glass_optimizer.domain.enums import GlassType


def test_parse_mm_european_and_numeric():
    assert parse_mm("383.000") == 383
    assert parse_mm("599.500") == 600       # 599.5 -> yukari yuvarlanir
    assert parse_mm("567.100") == 567
    assert parse_mm("1.554.000") == 1554    # iki nokta = binlik ayraci
    assert parse_mm("718.250") == 718
    assert parse_mm(599.5) == 600           # sayisal mm
    assert parse_mm(1492) == 1492


def test_parse_plate():
    assert parse_plate("6000X3210") == (6000, 3210)
    assert parse_plate("3302x2134") == (3302, 2134)


def test_infer_glass_type_and_thickness():
    assert infer_glass_type("SERT LOW-E TEC 15 4 MM") == GlassType.LOW_E
    assert infer_glass_type("DUZ CAM 4 MM") == GlassType.FLOAT
    assert infer_glass_type("DUZ CAM FUME 4 MM") == GlassType.FLOAT
    assert infer_thickness("DUZ CAM 8 MM") == 8.0
    assert infer_thickness("YUMUSAK LOW-E ENERJI 3 MM") == 3.0


def test_material_code_distinguishes_products():
    a = material_code("SERT LOW-E TEC 15 4 MM")
    b = material_code("SERT LOW-E EKO PRO CLEAR 4 MM")
    assert a != b
    # Ayni urun -> ayni kod
    assert material_code("DUZ CAM 4 MM") == material_code("DUZ CAM 4 MM")


def test_load_order_table_from_records():
    records = [
        {"PLAKA TIPI": "DUZ CAM 4 MM", "PLAKA EBAT": "6000X3210",
         "URUN EN": "383.000", "URUN BOY": "578.000", "URUN MIKTARI": 246},
        {"PLAKA TIPI": "SERT LOW-E TEC 15 4 MM", "PLAKA EBAT": "3302X2134",
         "URUN EN": "748.000", "URUN BOY": "599.500", "URUN MIKTARI": 100},
    ]
    job = load_order_table_from_records(records)
    validate_job(job.stock, job.parts, job.kerf)
    assert len(job.parts) == 2
    # Iki farkli material -> iki ayri eslestirme anahtari
    mats = {p.material for p in job.parts}
    assert len(mats) == 2
    lowe = next(p for p in job.parts if "LOW" in p.material)
    assert lowe.glass_type == GlassType.LOW_E
    assert lowe.height_mm == 600  # 599.5 yuvarlandi


def test_load_order_table_from_excel(tmp_path):
    df = pd.DataFrame(
        [
            ["DUZ CAM 4 MM", "6000X3210", "383.000", "578.000", 246],
            ["DUZ CAM 4 MM", "6000X3210", "320.000", "433.000", 479],
            ["SERT LOW-E EKO PRO CLEAR 4 MM", "3210X2000", "1.203.000", "772.900", 96],
        ],
        columns=["PLAKA TIPI", "PLAKA EBAT", "URUN EN", "URUN BOY", "URUN MIKTARI"],
    )
    path = tmp_path / "siparis.xlsx"
    df.to_excel(path, index=False)

    job = load_order_table_from_excel(path)
    validate_job(job.stock, job.parts, job.kerf)
    # Ayni urun + ebat satirlari ayni material'a duser
    duz = [p for p in job.parts if p.material == material_code("DUZ CAM 4 MM")]
    assert len(duz) == 2
    eko = next(p for p in job.parts if "EKO" in p.material)
    assert eko.width_mm == 1203 and eko.height_mm == 773


def test_missing_columns_raises(tmp_path):
    df = pd.DataFrame([{"foo": 1, "bar": 2}])
    path = tmp_path / "bad.xlsx"
    df.to_excel(path, index=False)
    with pytest.raises(ValueError):
        load_order_table_from_excel(path)
