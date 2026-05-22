"""Cam Kesim Optimizasyonu - Streamlit Arayuzu.

Calistirma:
    streamlit run streamlit_app.py
veya
    ./run_ui.sh        (macOS/Linux)
    run_ui.bat         (Windows)

Arayuz ile:
  - Stok plakalari ve parca siparislerini tablo halinde girebilir veya
    JSON yukleyebilirsiniz.
  - Kerf / kenar payi ve cozucu stratejisini secebilirsiniz.
  - Optimizasyonu calistirip ozet, plaka gorselleri, maliyet, fire ve
    kesim planini gorebilir; raporu indirebilirsiniz.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# src/ yolunu ekle (kurulum yapilmadan calistirma icin)
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from glass_optimizer.config.settings import OptimizerSettings  # noqa: E402
from glass_optimizer.data.validators import ValidationError, validate_job  # noqa: E402
from glass_optimizer.domain.enums import GlassType, GrainConstraint  # noqa: E402
from glass_optimizer.domain.models import (  # noqa: E402
    KerfSettings,
    PartOrder,
    StockSheet,
)
from glass_optimizer.optimization.multi_sheet import MultiSheetOrchestrator  # noqa: E402
from glass_optimizer.services.cost_calculator import calculate_cost  # noqa: E402
from glass_optimizer.services.cutting_plan import build_cutting_plan  # noqa: E402
from glass_optimizer.services.waste_analyzer import analyze_waste  # noqa: E402
from glass_optimizer.presentation.reporter import write_text_report  # noqa: E402
from glass_optimizer.presentation.visualizer import build_sheet_figure  # noqa: E402

GLASS_TYPES = [g.value for g in GlassType]
GRAINS = [g.value for g in GrainConstraint]
STRATEGIES = ["guillotine", "maxrects", "cpsat", "hybrid"]

st.set_page_config(page_title="Cam Kesim Optimizasyonu", layout="wide")


def _default_stock_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "sheet_id": "DUZ_CAM_4MM_6000x3210", "width_mm": 6000, "height_mm": 3210,
                "glass_type": "float", "thickness_mm": 4.0, "material": "DUZ_CAM_4MM",
                "quantity": 20, "unit_cost": 1500.0,
            },
            {
                "sheet_id": "SERT_LOWE_TEC15_4MM_3302x2134", "width_mm": 3302, "height_mm": 2134,
                "glass_type": "low_e", "thickness_mm": 4.0, "material": "SERT_LOWE_TEC15_4MM",
                "quantity": 20, "unit_cost": 1200.0,
            },
        ]
    )


def _default_parts_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"part_id": "DUZ-383x578", "width_mm": 383, "height_mm": 578,
             "quantity": 24, "glass_type": "float", "thickness_mm": 4.0,
             "material": "DUZ_CAM_4MM", "allow_rotation": True, "grain": "none", "priority": 5},
            {"part_id": "DUZ-320x433", "width_mm": 320, "height_mm": 433,
             "quantity": 47, "glass_type": "float", "thickness_mm": 4.0,
             "material": "DUZ_CAM_4MM", "allow_rotation": True, "grain": "none", "priority": 5},
            {"part_id": "LOWE-748x600", "width_mm": 748, "height_mm": 600,
             "quantity": 30, "glass_type": "low_e", "thickness_mm": 4.0,
             "material": "SERT_LOWE_TEC15_4MM", "allow_rotation": True, "grain": "none", "priority": 5},
        ]
    )


def _load_json_into_state(data: dict) -> None:
    kerf = data.get("kerf", {})
    st.session_state["kerf_mm"] = int(kerf.get("kerf_mm", 3))
    st.session_state["edge_trim_mm"] = int(kerf.get("edge_trim_mm", 10))
    st.session_state["min_offcut_mm"] = int(kerf.get("min_offcut_mm", 100))
    if data.get("stock"):
        st.session_state["stock_df"] = pd.DataFrame(data["stock"])
    if data.get("parts"):
        df = pd.DataFrame(data["parts"])
        for col, default in (("grain", "none"), ("allow_rotation", True),
                             ("priority", 5), ("thickness_mm", 4.0)):
            if col not in df.columns:
                df[col] = default
        st.session_state["parts_df"] = df


# ---- Oturum durumu ----------------------------------------------------------
if "stock_df" not in st.session_state:
    st.session_state["stock_df"] = _default_stock_df()
if "parts_df" not in st.session_state:
    st.session_state["parts_df"] = _default_parts_df()

st.title("🔷 Cam Kesim Optimizasyonu")
st.caption(
    "Guillotine-kisitli homojen-blok yerlestirme · OR-Tools CP-SAT · MaxRects"
)

# ---- Kenar cubugu: ayarlar --------------------------------------------------
with st.sidebar:
    st.header("⚙️ Ayarlar")

    strategy = st.selectbox(
        "Strateji", STRATEGIES, index=0,
        help="guillotine: cam koprusu icin zorunlu (varsayilan). "
             "maxrects/hybrid: serbest kesim (su jeti/lazer).",
    )
    time_limit = st.slider(
        "Plaka basina cozucu suresi (s)", 1, 120, 10,
        help="CP-SAT iceren stratejiler icin sure siniri.",
    )

    st.subheader("Kesim Parametreleri")
    kerf_mm = st.number_input(
        "Kerf - testere kalinligi (mm)", 0, 50,
        st.session_state.get("kerf_mm", 3),
    )
    edge_trim_mm = st.number_input(
        "Kenar payi (mm)", 0, 100,
        st.session_state.get("edge_trim_mm", 10),
    )
    min_offcut_mm = st.number_input(
        "Min. kullanilabilir fire (mm)", 0, 1000,
        st.session_state.get("min_offcut_mm", 100),
    )

    st.divider()
    st.subheader("JSON Yukle")
    uploaded = st.file_uploader("Is dosyasi (.json)", type=["json"])
    if uploaded is not None:
        try:
            _load_json_into_state(json.loads(uploaded.read().decode("utf-8")))
            st.success("JSON yuklendi. Tablolar guncellendi.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"JSON okunamadi: {exc}")

# ---- Girdi tablolari --------------------------------------------------------
st.subheader("📦 Stok Plakalari")
st.caption(
    "`material`: urun/malzeme kodu. Ayni cam tipi+kalinligi paylasan ama "
    "birbirine donusturulemeyen urunler (orn. Low-E TEC 15 ile EKO PRO) "
    "ayni material'a sahip stok ve parcalar arasinda eslesir."
)
stock_df = st.data_editor(
    st.session_state["stock_df"],
    num_rows="dynamic",
    use_container_width=True,
    key="stock_editor",
    column_config={
        "glass_type": st.column_config.SelectboxColumn("glass_type", options=GLASS_TYPES),
        "width_mm": st.column_config.NumberColumn("width_mm", min_value=1),
        "height_mm": st.column_config.NumberColumn("height_mm", min_value=1),
        "quantity": st.column_config.NumberColumn("quantity", min_value=1, step=1),
        "unit_cost": st.column_config.NumberColumn("unit_cost", min_value=0.0),
    },
)

st.subheader("✂️ Parca Siparisleri")
parts_df = st.data_editor(
    st.session_state["parts_df"],
    num_rows="dynamic",
    use_container_width=True,
    key="parts_editor",
    column_config={
        "glass_type": st.column_config.SelectboxColumn("glass_type", options=GLASS_TYPES),
        "grain": st.column_config.SelectboxColumn("grain", options=GRAINS),
        "allow_rotation": st.column_config.CheckboxColumn("allow_rotation"),
        "width_mm": st.column_config.NumberColumn("width_mm", min_value=1),
        "height_mm": st.column_config.NumberColumn("height_mm", min_value=1),
        "quantity": st.column_config.NumberColumn("quantity", min_value=1, step=1),
        "priority": st.column_config.NumberColumn("priority", min_value=1, max_value=10, step=1),
    },
)

run = st.button("🚀 Optimizasyonu Calistir", type="primary", use_container_width=True)


def _build_models():
    kerf = KerfSettings(
        kerf_mm=int(kerf_mm),
        edge_trim_mm=int(edge_trim_mm),
        min_offcut_mm=int(min_offcut_mm),
    )
    stock = [StockSheet(**row) for row in stock_df.to_dict(orient="records")]
    parts = [PartOrder(**row) for row in parts_df.to_dict(orient="records")]
    return stock, parts, kerf


if run:
    try:
        stock, parts, kerf = _build_models()
        validate_job(stock, parts, kerf)
    except (ValidationError, ValueError, TypeError) as exc:
        st.error(f"Girdi hatasi: {exc}")
        st.stop()

    settings = OptimizerSettings(
        strategy=strategy, time_limit_s=float(time_limit),
        cpsat_polish_time_s=float(time_limit),
    )
    with st.spinner("Optimizasyon calisiyor..."):
        result = MultiSheetOrchestrator(settings).solve(stock, parts, kerf)

    st.session_state["result"] = result

# ---- Sonuclar ---------------------------------------------------------------
result = st.session_state.get("result")
if result is not None:
    st.divider()
    st.header("📊 Sonuclar")

    cost = calculate_cost(result)
    waste = analyze_waste(result, result.kerf)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kullanilan plaka", result.sheets_used)
    c2.metric("Genel verim", f"%{result.overall_utilization * 100:.1f}")
    c3.metric("Toplam fire", f"{result.total_waste_area_mm2 / 1e6:.2f} m²")
    c4.metric("Sure", f"{result.total_runtime_s:.2f} s")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Hammadde maliyeti", f"{cost.raw_material_cost:,.0f}")
    c6.metric("Fire degeri", f"{cost.waste_value:,.0f}")
    c7.metric("Yerlesemeyen parca", cost.unplaced_count)
    c8.metric("Geri kazanilabilir fire", f"{waste.reusable_offcut_m2:.2f} m²")

    if result.unplaced_parts:
        st.warning(
            "Bazi parcalar yerlestirilemedi (stok yetersiz olabilir): "
            + ", ".join(f"{p.part_id} x{p.quantity}" for p in result.unplaced_parts)
        )

    tab_vis, tab_sheets, tab_plan, tab_dl = st.tabs(
        ["🖼️ Plaka Gorselleri", "📋 Plaka Detaylari", "🔪 Kesim Plani", "⬇️ Indir"]
    )

    with tab_vis:
        for idx, sheet in enumerate(result.sheets, start=1):
            fig = build_sheet_figure(sheet, idx, result.kerf.edge_trim_mm)
            st.pyplot(fig, use_container_width=True)

    with tab_sheets:
        rows = [
            {
                "#": i, "Plaka": s.stock.sheet_id,
                "Boyut": f"{s.stock.width_mm}x{s.stock.height_mm}",
                "Cam": s.stock.glass_type.value,
                "Parca": len(s.placements),
                "Verim %": round(s.utilization * 100, 1),
            }
            for i, s in enumerate(result.sheets, start=1)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if waste.reusable_offcuts:
            st.subheader("Yeniden Kullanilabilir Fireler")
            oc_rows = [
                {
                    "Plaka": oc.sheet_id, "x": oc.x_mm, "y": oc.y_mm,
                    "Boyut": f"{oc.width_mm}x{oc.height_mm}",
                    "Alan m²": round(oc.area_m2, 3),
                }
                for oc in waste.reusable_offcuts
            ]
            st.dataframe(pd.DataFrame(oc_rows), use_container_width=True, hide_index=True)

    with tab_plan:
        plan = build_cutting_plan(result)
        for sp in plan.sheet_plans:
            with st.expander(f"Plaka: {sp.sheet_id} ({len(sp.instructions)} kesim)"):
                plan_rows = [
                    {
                        "Adim": ins.step, "Parca": ins.part_id,
                        "x": ins.x_mm, "y": ins.y_mm,
                        "Boyut": f"{ins.width_mm}x{ins.height_mm}",
                    }
                    for ins in sp.instructions
                ]
                st.dataframe(pd.DataFrame(plan_rows), use_container_width=True, hide_index=True)

    with tab_dl:
        report_path = ROOT / "output" / "report.txt"
        report_path.parent.mkdir(exist_ok=True)
        write_text_report(result, report_path)
        st.download_button(
            "📄 Metin raporunu indir (report.txt)",
            data=report_path.read_text(encoding="utf-8"),
            file_name="cam_kesim_raporu.txt",
            mime="text/plain",
        )
        input_json = {
            "kerf": {"kerf_mm": int(kerf_mm), "edge_trim_mm": int(edge_trim_mm),
                     "min_offcut_mm": int(min_offcut_mm)},
            "stock": stock_df.to_dict(orient="records"),
            "parts": parts_df.to_dict(orient="records"),
        }
        st.download_button(
            "🧾 Girdiyi JSON olarak indir",
            data=json.dumps(input_json, ensure_ascii=False, indent=2),
            file_name="cam_kesim_girdi.json",
            mime="application/json",
        )
else:
    st.info("Girdileri duzenleyip **Optimizasyonu Calistir** butonuna basin.")
