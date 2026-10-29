from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboard import components, overview, period_analysis, raw_data, vehicle_analysis
from dashboard.data_service import clear_dashboard_cache, get_dashboard_data
from dashboard.styles import apply_dashboard_styles
from dashboard.theme import init_theme_state, is_dark_theme, set_theme_from_toggle


st.set_page_config(
    page_title="แดชบอร์ดรถค้างอาคาร",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)


init_theme_state()
apply_dashboard_styles(is_dark_theme())


DASHBOARD_SECTIONS = {
    "overview": "› ภาพรวมแดชบอร์ด",
    "period": "› วิเคราะห์ตามช่วงเวลา",
    "vehicle": "› วิเคราะห์รายคัน / ค้างคืน",
    "raw": "› ตารางข้อมูลดิบ / ส่งออก",
}


if "dashboard_section" not in st.session_state:
    st.session_state.dashboard_section = "overview"


def _render_section(error_message: str, renderer, data) -> None:
    try:
        renderer(data)
    except Exception as exc:
        st.error(error_message)
        with st.expander("รายละเอียดสำหรับผู้ดูแลระบบ"):
            st.exception(exc)


st.sidebar.page_link("app_parking.py", label="› กลับหน้าบันทึกข้อมูล")
st.sidebar.markdown("---")
if st.sidebar.button("รีเฟรชข้อมูล", width="stretch"):
    clear_dashboard_cache()
    st.rerun()
st.sidebar.markdown("---")
result = get_dashboard_data()
header_content, header_theme = st.columns([4, 1], vertical_alignment="center")
with header_content:
    components.render_hero(
        "ประวัติและแดชบอร์ด",
        "ตรวจสอบทะเบียนย้อนหลัง วิเคราะห์การจอด และส่งออกรายงาน",
        result.loaded_at,
    )
with header_theme:
    st.session_state.dark_mode_toggle = is_dark_theme()
    st.toggle("โหมดกลางคืน", key="dark_mode_toggle", on_change=set_theme_from_toggle)
with st.container(horizontal=True, key="parking_navigation", gap="xsmall"):
    st.page_link("app_parking.py", label="บันทึกทะเบียน", icon=":material/edit_note:")
    st.page_link("pages/dashboard.py", label="ประวัติและแดชบอร์ด", icon=":material/space_dashboard:")
st.session_state.dashboard_section = st.segmented_control(
    "เมนูประวัติและรายงาน",
    options=list(DASHBOARD_SECTIONS),
    format_func=lambda value: DASHBOARD_SECTIONS[value].replace("› ", ""),
    default=st.session_state.dashboard_section,
    selection_mode="single",
    key="dashboard_section_selector",
) or "overview"

if result.error:
    components.render_error(result.error)
elif result.prepared.empty:
    if result.raw.empty:
        components.render_empty("ยังไม่มีรายการบันทึก เริ่มเพิ่มทะเบียนได้ที่หน้าบันทึกข้อมูล")
    else:
        components.render_empty("พบข้อมูลในชีท แต่รูปแบบวันที่หรือทะเบียนยังไม่พร้อมแสดงผล กรุณาติดต่อผู้ดูแล")
else:
    invalid_rows = int(pd.to_datetime(result.raw["วันที่ตรวจพบ"], errors="coerce").isna().sum())
    if invalid_rows:
        st.warning(f"มี {invalid_rows} รายการที่รูปแบบวันที่ไม่ถูกต้อง จึงไม่นำมาคำนวณ")
    st.caption(f"ข้อมูลพร้อมแสดงผล {len(result.prepared):,} รายการ · รวมประวัติย้อนหลัง")
    selected_section = st.session_state.dashboard_section
    if selected_section == "overview":
        _render_section("ไม่สามารถแสดงผลภาพรวมแดชบอร์ดได้", overview.render, result.prepared)
    elif selected_section == "period":
        _render_section("ไม่สามารถแสดงผลวิเคราะห์ตามช่วงเวลาได้", period_analysis.render, result.prepared)
    elif selected_section == "vehicle":
        _render_section("ไม่สามารถแสดงผลวิเคราะห์รายคันได้", vehicle_analysis.render, result.prepared)
    else:
        _render_section("ไม่สามารถแสดงผลตารางข้อมูลดิบได้", raw_data.render, result.prepared)
