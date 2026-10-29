from __future__ import annotations

from services.parking_domain import bangkok_now

import pandas as pd
import streamlit as st

from dashboard import components
from dashboard.data_service import clear_dashboard_cache, to_csv_bytes, to_excel_bytes
from dashboard.display import prepare_display_dataframe
from dashboard.metrics import filter_dataframe


def render(df: pd.DataFrame) -> None:
    filters = components.render_filter_bar(df, "raw")
    if filters.get("refresh"):
        clear_dashboard_cache()
        st.rerun()

    filtered = filter_dataframe(
        df,
        buildings=filters["buildings"],
        provinces=filters["provinces"],
        year=filters["year"],
        month=filters["month"],
        date_range=filters["date_range"],
    )

    search = st.text_input(
        "ค้นหาในตาราง",
        placeholder="ค้นทะเบียนรถ อาคาร จังหวัด หมายเหตุ หรือเหตุผลค้างคืน",
        key="raw_search",
    )
    filtered = filter_dataframe(filtered, search_text=search)
    show_system_cols = st.toggle(
        "แสดงคอลัมน์ระบบ/คอลัมน์ที่คำนวณเพิ่ม",
        value=False,
        key="raw_show_system_cols",
    )

    if filtered.empty:
        components.render_empty("ไม่พบรายการที่ตรงกับตัวกรอง ลองปรับช่วงเวลาหรือล้างตัวกรอง")
        return
    st.caption(f"ช่วงข้อมูล {filtered['วันที่ตรวจพบ'].min():%d/%m/%Y} – {filtered['วันที่ตรวจพบ'].max():%d/%m/%Y} · {len(filtered):,} รายการ")
    try:
        display_df = prepare_display_dataframe(filtered, include_system_columns=show_system_cols)
        if not display_df.columns.is_unique:
            raise ValueError("Duplicate column names found")
        st.caption(f"จำนวนรายการหลังกรอง: {len(display_df):,} รายการ")
        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
            column_config={
                "วันที่": st.column_config.TextColumn("วันที่"),
                "ทะเบียนรถ": st.column_config.TextColumn("ทะเบียนรถ"),
                "จังหวัด": st.column_config.TextColumn("จังหวัด"),
                "อาคาร": st.column_config.TextColumn("อาคาร"),
                "สถานะค้างคืน": st.column_config.TextColumn("สถานะค้างคืน"),
                "เหตุผลค้างคืน": st.column_config.TextColumn("เหตุผลค้างคืน"),
            },
        )
    except Exception as exc:
        if "Duplicate column" in str(exc):
            st.error("ไม่สามารถแสดงตารางข้อมูลได้ เนื่องจากพบชื่อคอลัมน์ซ้ำ")
        else:
            st.error("ไม่สามารถแสดงตารางข้อมูลได้")
        with st.expander("รายละเอียดสำหรับผู้ดูแลระบบ"):
            st.exception(exc)
        return

    st.markdown("**ส่งออกรายการที่แสดงอยู่**")
    col_csv, col_excel = st.columns(2)
    today_key = bangkok_now().date().strftime("%Y-%m-%d")
    with col_csv:
        st.download_button(
            "ดาวน์โหลด CSV",
            data=to_csv_bytes(display_df),
            file_name=f"nacc_parking_export_{today_key}.csv",
            mime="text/csv",
            width="stretch",
        )
    with col_excel:
        try:
            excel_bytes = to_excel_bytes(display_df)
            st.download_button(
                "ดาวน์โหลด Excel",
                data=excel_bytes,
                file_name=f"nacc_parking_export_{today_key}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
        except Exception as exc:
            st.warning(f"ยังไม่สามารถสร้าง Excel ได้: {exc}")
