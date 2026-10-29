from __future__ import annotations

from services.parking_domain import bangkok_now
import html
from datetime import date, datetime

import pandas as pd
import streamlit as st


DATE_CANDIDATES = [
    "record_datetime",
    "date_key",
    "วันที่ตรวจพบ",
    "วันที่บันทึก",
    "วันที่พบ",
    "Timestamp",
    "Date",
    "created_at",
    "found_date",
]
BUILDING_CANDIDATES = ["อาคาร", "building", "สถานที่", "location", "building_name"]


def get_today_records(df: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=list(df.columns) if df is not None else [])

    today = today or bangkok_now().date()
    date_col = _find_column(df, DATE_CANDIDATES)
    if date_col is None:
        return df.iloc[0:0].copy()

    parsed_dates = _parse_dates(df[date_col])
    return df[parsed_dates.dt.date == today].copy()


def get_today_building_counts(
    df: pd.DataFrame,
    buildings: list[str],
    today: date | None = None,
) -> list[dict[str, object]]:
    today_df = get_today_records(df, today=today)
    building_col = _find_column(today_df, BUILDING_CANDIDATES)
    if building_col is None:
        building_counts = pd.Series(dtype="int64")
    else:
        building_values = today_df[building_col].fillna("").astype(str).str.strip()
        building_counts = building_values.value_counts()

    cards = []
    for building in _first_five_buildings(buildings):
        if building:
            count = int(building_counts.get(str(building).strip(), 0))
            cards.append({"label": str(building).strip(), "count": count, "kind": "building"})
        else:
            cards.append({"label": "ยังไม่มีอาคาร", "count": 0, "kind": "empty"})

    cards.append({"label": "รวมทุกอาคาร", "count": int(len(today_df)), "kind": "total"})
    return cards


def render_home_mini_dashboard(
    df: pd.DataFrame,
    buildings: list[str],
    is_dark: bool | None = None,
    error_message: str | None = None,
    loaded_at: datetime | None = None,
) -> None:
    theme_attr = "" if is_dark is None else f' data-theme="{"dark" if is_dark else "light"}"'
    if error_message:
        _render_html(
            f'<div class="mini-dashboard-shell"{theme_attr}>'
            '<div class="mini-dashboard-error">ไม่สามารถโหลดข้อมูลสรุปวันนี้ได้</div>'
            '</div>'
        )
        return

    cards = get_today_building_counts(df, buildings)
    current = {str(card["label"]): int(card["count"]) for card in cards}
    today = bangkok_now().date()
    previous = st.session_state.get("home_summary_snapshot", {}) if st.session_state.get("home_summary_date") == today else {}
    changes = {label: count - previous[label] for label, count in current.items() if label in previous and count != previous[label]}
    st.session_state.home_summary_snapshot = current
    st.session_state.home_summary_date = today
    _render_html(_build_dashboard_markup(cards, theme_attr=theme_attr, changes=changes, loaded_at=loaded_at))


def _build_dashboard_markup(cards, theme_attr="", changes=None, loaded_at=None):
    changes = changes or {}
    total = next((card for card in cards if card["kind"] == "total"), None)
    ordered = ([total] if total else []) + [card for card in cards if card["kind"] != "total"]
    cards_html = "".join(_render_card(card, changes.get(str(card["label"]), 0)) for card in ordered)
    checked = loaded_at.strftime("%H:%M:%S") if loaded_at else "—"
    total_change = changes.get("รวมทุกอาคาร", 0)
    feedback = f"ยอดรวมเพิ่มขึ้น {total_change} รายการ" if total_change > 0 else f"ยอดรวมลดลง {abs(total_change)} รายการ" if total_change < 0 else ""
    return (
        f'<section class="mini-dashboard-shell"{theme_attr} aria-label="ยอดบันทึกวันนี้">'
        '<div class="mini-dashboard-heading"><h2>ยอดบันทึกวันนี้</h2>'
        f'<span class="summary-business-date">{bangkok_now():%d/%m/%Y}</span></div>'
        '<div class="mini-dashboard-wrap" aria-label="สรุปยอดบันทึกรถวันนี้">'
        f'<div class="mini-dashboard-grid">{cards_html}</div></div>'
        f'<div class="summary-freshness"><span class="summary-status-dot" aria-hidden="true"></span>อัปเดตจากชีท {checked} · รีเฟรชทุก 30 วินาที</div>'
        f'<div class="summary-change-announcement" role="status" aria-live="polite">{feedback}</div></section>'
    )


def _render_card(card, change=0):
    label = html.escape(str(card["label"]))
    count = html.escape(f"{int(card['count']):,}")
    kind = html.escape(str(card["kind"]))
    changed = " mini-stat-card--updated" if change else ""
    delta = f'<span class="mini-stat-delta">{change:+,}</span>' if change else ''
    return (
        f'<div class="mini-stat-card mini-stat-card--{kind}{changed}">'
        f'<div class="mini-stat-top"><span class="mini-stat-title">{label}</span></div>'
        f'<div class="mini-stat-reading"><span class="mini-stat-value">{count}</span>{delta}</div>'
        '<span class="mini-stat-subtitle">รายการวันนี้</span></div>'
    )


def _render_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)



def _first_five_buildings(buildings: list[str]) -> list[str | None]:
    cleaned = [str(building).strip() for building in buildings if str(building).strip()]
    selected: list[str | None] = cleaned[:5]
    while len(selected) < 5:
        selected.append(None)
    return selected


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {_normalize_column_name(column): column for column in df.columns}
    for candidate in candidates:
        found = lookup.get(_normalize_column_name(candidate))
        if found is not None:
            return found
    return None


def _normalize_column_name(value: object) -> str:
    return str(value).strip().lower().replace("_", "").replace("-", "").replace(" ", "")


def _parse_dates(series: pd.Series) -> pd.Series:
    as_text = series.astype(str).str.strip()
    parsed = pd.to_datetime(series, errors="coerce")
    slash_mask = as_text.str.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", na=False)
    if slash_mask.any():
        parsed.loc[slash_mask] = pd.to_datetime(
            as_text.loc[slash_mask],
            dayfirst=True,
            errors="coerce",
        )
    return pd.Series(parsed, index=series.index)
