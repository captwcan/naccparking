import streamlit as st
from datetime import date, datetime, timedelta
import pandas as pd
import os
from pathlib import Path
import json
import gspread
from google.oauth2.service_account import Credentials
import re
from services.parking_domain import bangkok_now, vehicle_key
from dashboard.data_service import clear_dashboard_cache
from dashboard.home_summary import render_home_mini_dashboard
from dashboard.theme import apply_theme_css, init_theme_state, is_dark_theme, render_theme_switch
from parking_analysis import summarize_long_parkers
from report_generator import (
    build_detailed_report,
    get_report_font_options,
    get_report_period,
    make_report_filename,
    to_csv_bytes,
    to_summary_jpg_bytes,
    to_summary_pdf_bytes,
)
from services.google_sheets_service import (
    append_parking_rows,
    batch_delete_rows,
    read_parking_values,
    cancel_parking_records,
    read_all_parking_values,
    read_buildings,
    write_buildings,
)

# การตั้งค่าหน้าจอเบื้องต้น
st.set_page_config(
    page_title="ระบบบันทึกรถค้างอาคาร",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- THEME MANAGEMENT -----------------
init_theme_state()

apply_theme_css()

# ----------------- DATA MANAGEMENT (GOOGLE SHEETS) -----------------
@st.cache_resource
def init_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    if "gcp_service_account" not in st.secrets:
        st.error("❌ ไม่พบข้อมูล gcp_service_account ใน st.secrets")
        st.stop()

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)

    if "spreadsheet_url" not in st.secrets:
        st.error("❌ ไม่พบข้อมูล spreadsheet_url ใน st.secrets")
        st.stop()

    spreadsheet = client.open_by_url(st.secrets["spreadsheet_url"])
    return spreadsheet.worksheet("RawData")

@st.cache_data(ttl=25, show_spinner=False)
def load_raw_parking_values():
    return read_all_parking_values(init_connection().spreadsheet), bangkok_now()


def load_data():
    columns = ["วันที่ตรวจพบ", "อาคาร", "ทะเบียนรถ", "จังหวัด"]
    st.session_state["load_data_error"] = None

    try:
        values, loaded_at = load_raw_parking_values()
        st.session_state.summary_loaded_at = loaded_at

        if len(values) > 1:
            return pd.DataFrame(values[1:], columns=columns)
        else:
            return pd.DataFrame(columns=columns)

    except Exception as e:
        st.session_state["load_data_error"] = str(e)
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        return pd.DataFrame(columns=columns)

BUILDINGS_FILE = Path(__file__).resolve().with_name("buildings.json")

def load_buildings():
    defaults = json.loads(BUILDINGS_FILE.read_text(encoding="utf-8"))
    return read_buildings(init_connection().spreadsheet, defaults)

def save_buildings(buildings_list):
    write_buildings(init_connection().spreadsheet, buildings_list)


buildings_list = load_buildings()

def add_row_numbers(df):
    display_df = df.reset_index(drop=True).copy()
    display_df.insert(0, "ลำดับ", range(1, len(display_df) + 1))
    return display_df

@st.fragment(run_every="30s")
def render_home_summary_placeholder(placeholder):
    home_summary_df = load_data()
    with placeholder.container(border=True, key="parking_summary_panel"):
        render_home_mini_dashboard(
            home_summary_df,
            buildings_list,
            is_dark=is_dark_theme(),
            error_message=st.session_state.get("load_data_error"),
            loaded_at=st.session_state.get("summary_loaded_at"),
        )
        with st.container(horizontal=True, horizontal_alignment="right", key="parking_summary_refresh"):
            st.button("รีเฟรชยอด", icon=":material/refresh:", key="refresh_home_summary", on_click=load_raw_parking_values.clear)

MAX_VEHICLE_ROWS = 100
DEFAULT_PROVINCE = "กรุงเทพมหานคร"

def init_vehicle_rows():
    if "vehicle_rows" not in st.session_state or not st.session_state.vehicle_rows:
        st.session_state.vehicle_rows = [{"id": 1}]
    if "next_vehicle_id" not in st.session_state:
        max_id = max(row["id"] for row in st.session_state.vehicle_rows)
        st.session_state.next_vehicle_id = max_id + 1
    if "vehicle_count_widget_version" not in st.session_state:
        st.session_state.vehicle_count_widget_version = 0
    for row in st.session_state.vehicle_rows:
        row_id = row["id"]
        draft = st.session_state.get("vehicle_drafts", {}).get(row_id, {})
        for field in ("plate", "province"):
            key = f"{field}_{row_id}"
            if key not in st.session_state and field in draft:
                st.session_state[key] = draft[field]


def remember_vehicle_draft(row_id):
    drafts = st.session_state.setdefault("vehicle_drafts", {})
    drafts[row_id] = {
        "plate": st.session_state.get(f"plate_{row_id}", ""),
        "province": st.session_state.get(f"province_{row_id}", DEFAULT_PROVINCE),
    }


def remember_building():
    st.session_state.draft_building = st.session_state.recording_building

def refresh_vehicle_count_widget():
    st.session_state.vehicle_count_widget_version += 1

def add_vehicle_row():
    if len(st.session_state.vehicle_rows) >= MAX_VEHICLE_ROWS:
        st.session_state.vehicle_row_warning = f"เพิ่มได้สูงสุด {MAX_VEHICLE_ROWS} รายการ"
        return
    row_id = st.session_state.next_vehicle_id
    st.session_state.vehicle_rows.append({"id": row_id})
    st.session_state.next_vehicle_id += 1
    refresh_vehicle_count_widget()

def request_clear_vehicle_rows():
    if any(str(st.session_state.get(f"plate_{row['id']}", "")).strip() for row in st.session_state.vehicle_rows):
        st.session_state.confirm_clear = True
    else:
        clear_vehicle_rows()

def clear_vehicle_rows():
    st.session_state.confirm_clear = False
    st.session_state.vehicle_drafts = {}
    for row in st.session_state.get("vehicle_rows", []):
        row_id = row["id"]
        st.session_state.pop(f"plate_{row_id}", None)
        st.session_state.pop(f"province_{row_id}", None)
    st.session_state.vehicle_rows = [{"id": st.session_state.get("next_vehicle_id", 1)}]
    st.session_state.next_vehicle_id = st.session_state.vehicle_rows[0]["id"] + 1
    refresh_vehicle_count_widget()

def delete_vehicle_row(row_id):
    st.session_state.get("vehicle_drafts", {}).pop(row_id, None)
    rows = st.session_state.vehicle_rows
    if len(rows) <= 1:
        st.session_state[f"plate_{row_id}"] = ""
        st.session_state[f"province_{row_id}"] = DEFAULT_PROVINCE
        st.session_state.vehicle_row_warning = "ต้องมีอย่างน้อย 1 รายการ จึงล้างข้อมูลในแถวนี้แทน"
        refresh_vehicle_count_widget()
        return
    st.session_state.vehicle_rows = [row for row in rows if row["id"] != row_id]
    st.session_state.pop(f"plate_{row_id}", None)
    st.session_state.pop(f"province_{row_id}", None)
    refresh_vehicle_count_widget()

def sync_vehicle_count_to_target(count_key):
    target = int(st.session_state.get(count_key, 1))
    target = max(1, min(MAX_VEHICLE_ROWS, target))
    while len(st.session_state.vehicle_rows) < target:
        row_id = st.session_state.next_vehicle_id
        st.session_state.vehicle_rows.append({"id": row_id})
        st.session_state.next_vehicle_id += 1
    while len(st.session_state.vehicle_rows) > target:
        row = st.session_state.vehicle_rows.pop()
        row_id = row["id"]
        st.session_state.get("vehicle_drafts", {}).pop(row_id, None)
        st.session_state.pop(f"plate_{row_id}", None)
        st.session_state.pop(f"province_{row_id}", None)
    refresh_vehicle_count_widget()

def collect_vehicle_entries():
    entries = []
    skipped = 0
    for row in st.session_state.vehicle_rows:
        row_id = row["id"]
        plate = st.session_state.get(f"plate_{row_id}", "").strip()
        province = st.session_state.get(f"province_{row_id}", DEFAULT_PROVINCE)
        if not plate:
            skipped += 1
            continue
        entries.append({"row_id": row_id, "plate": plate, "province": province})
    return entries, skipped

def duplicate_key(plate, province):
    return vehicle_key(plate, province)

def find_form_duplicates(entries):
    seen = {}
    duplicates = []
    for entry in entries:
        key = duplicate_key(entry["plate"], entry["province"])
        if key in seen:
            duplicates.append(entry)
        else:
            seen[key] = entry
    return duplicates

def find_sheet_duplicates(records, current_date, entries):
    existing = set()
    for row in records:
        if len(row) >= 4 and row[0] == current_date:
            existing.add(duplicate_key(row[2], row[3]))
    return [entry for entry in entries if duplicate_key(entry["plate"], entry["province"]) in existing]

def format_vehicle_list(entries):
    return "\n".join(f"- {entry['plate']} {entry['province']}" for entry in entries)

def parse_updated_rows(response, row_count):
    updated_range = response.get("updates", {}).get("updatedRange", "") if isinstance(response, dict) else ""
    if not updated_range:
        return []
    match = re.search(r"![A-Z]+(\d+):[A-Z]+(\d+)", updated_range)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        return list(range(start, end + 1))
    match = re.search(r"[A-Z]+(\d+)", updated_range)
    if match:
        start = int(match.group(1))
        return list(range(start, start + row_count))
    return []

def find_batch_rows_from_sheet(records, batch):
    rows_to_delete = []
    used_indexes = set()
    for item in reversed(batch):
        for index in range(len(records) - 1, -1, -1):
            if index in used_indexes:
                continue
            row = records[index]
            if (
                len(row) >= 4
                and row[0] == item["date"]
                and row[1] == item["building"]
                and row[2] == item["plate"]
                and row[3] == item["province"]
            ):
                used_indexes.add(index)
                rows_to_delete.append(index + 1)
                break
    return rows_to_delete

THAI_MONTHS = [
    (1, "มกราคม"),
    (2, "กุมภาพันธ์"),
    (3, "มีนาคม"),
    (4, "เมษายน"),
    (5, "พฤษภาคม"),
    (6, "มิถุนายน"),
    (7, "กรกฎาคม"),
    (8, "สิงหาคม"),
    (9, "กันยายน"),
    (10, "ตุลาคม"),
    (11, "พฤศจิกายน"),
    (12, "ธันวาคม"),
]

def select_report_date(report_type):
    today = bangkok_now().date()

    if report_type == "รายวัน":
        return st.date_input("เลือกวันที่", value=today)

    year_options = list(range(today.year - 3, today.year + 2))
    month_labels = [label for _, label in THAI_MONTHS]

    col_month, col_year = st.columns(2)
    with col_month:
        selected_month_label = st.selectbox(
            "เลือกเดือน",
            month_labels,
            index=today.month - 1,
            key=f"{report_type}_month",
        )
    with col_year:
        selected_year = st.selectbox(
            "เลือกปี",
            year_options,
            index=year_options.index(today.year),
            key=f"{report_type}_year",
        )

    selected_month = dict((label, month) for month, label in THAI_MONTHS)[selected_month_label]

    if report_type == "รายเดือน":
        return date(selected_year, selected_month, 1)

    week_options = build_week_options(selected_year, selected_month)
    default_week_index = find_default_week_index(week_options, today)
    selected_week = st.selectbox(
        "เลือกสัปดาห์",
        week_options,
        index=default_week_index,
        format_func=lambda week: week["label"],
    )
    return selected_week["start"]

def build_week_options(year, month):
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    week_start = first_day - timedelta(days=first_day.weekday())
    weeks = []
    while week_start <= last_day:
        week_end = week_start + timedelta(days=6)
        weeks.append(
            {
                "start": week_start,
                "end": week_end,
                "label": f"{week_start:%d/%m/%Y} - {week_end:%d/%m/%Y}",
            }
        )
        week_start += timedelta(days=7)
    return weeks

def find_default_week_index(week_options, selected_date):
    for index, week in enumerate(week_options):
        if week["start"] <= selected_date <= week["end"]:
            return index
    return 0

# ----------------- ADMIN SETTINGS (SIDEBAR) -----------------
st.sidebar.markdown("## 🛠️ ตั้งค่าผู้ดูแลระบบ (Admin)")

st.sidebar.markdown("### 📈 รายงานและแดชบอร์ด")
if hasattr(st.sidebar, "page_link"):
    st.sidebar.page_link("pages/dashboard.py", label="› 📈 แดชบอร์ดภาพรวม")
elif hasattr(st, "switch_page"):
    if st.sidebar.button("› 📈 แดชบอร์ดภาพรวม", width="stretch"):
        st.switch_page("pages/dashboard.py")
else:
    st.sidebar.caption("เปิดแดชบอร์ดจากเมนู Pages ของ Streamlit")
st.sidebar.markdown("---")
with st.sidebar.expander("📝 จัดการรายชื่ออาคาร", expanded=False):
    new_bldg = st.text_input("ชื่ออาคารใหม่:")
    if st.button("➕ เพิ่มอาคาร", width="stretch"):
        if new_bldg and new_bldg not in buildings_list:
            buildings_list.append(new_bldg)
            save_buildings(buildings_list)
            st.success(f"เพิ่มอาคาร '{new_bldg}' สำเร็จ!")
            st.rerun()
        elif new_bldg in buildings_list:
            st.error("อาคารนี้มีอยู่ในระบบแล้ว")

    if buildings_list:
        bldg_to_delete = st.selectbox("เลือกอาคารที่ต้องการลบ:", buildings_list)
        if st.button("🗑️ ลบอาคาร", width="stretch"):
            buildings_list.remove(bldg_to_delete)
            save_buildings(buildings_list)
            st.warning(f"ลบอาคาร '{bldg_to_delete}' สำเร็จ!")
            st.rerun()

with st.sidebar.expander("📊 ข้อมูลตาราง Google Sheets", expanded=False):
    st.write("ใส่รหัสผ่านเพื่อดูข้อมูลตาราง")
    admin_pwd = st.text_input("รหัสผ่าน (Password):", type="password")
    # ตั้งรหัสผ่านง่ายๆ ไว้ที่ 1234 (แอดมินเปลี่ยนเองได้ในโค้ด)
    if admin_pwd == "1234":
        try:
            df_display = load_data()

            tab1, tab2 = st.tabs(["📝 ข้อมูลทั้งหมด", "🚨 สรุปข้อมูลรถจอดนาน"])

            with tab1:
                current_date = bangkok_now().strftime("%Y-%m-%d")

                df_today = df_display[df_display["วันที่ตรวจพบ"].astype(str) == current_date]

                st.dataframe(add_row_numbers(df_today), width="stretch", hide_index=True)
                st.success(f"โหลดข้อมูลประจำวันที่ {current_date} ทั้งหมด {len(df_today)} รายการ")

            with tab2:
                st.write("**วิเคราะห์รถที่จอดข้ามคืนสะสม**")
                days_threshold = st.number_input("กรองเฉพาะรถที่จอดสะสมตั้งแต่ (วัน):", min_value=1, value=7, step=1)

                if not df_display.empty:
                    long_parkers = summarize_long_parkers(df_display, days_threshold)

                    if not long_parkers.empty:
                        st.dataframe(add_row_numbers(long_parkers), width="stretch", hide_index=True)
                        st.warning(f"พบรถที่จอดสะสม {days_threshold} วันขึ้นไป จำนวน {len(long_parkers)} คัน")
                    else:
                        st.success(f"ยังไม่พบรถที่จอดสะสมถึง {days_threshold} วัน 🎉")
                else:
                    st.info("ยังไม่มีข้อมูลในระบบ")
        except Exception as e:
            st.error(f"ไม่สามารถโหลดข้อมูลได้: {e}")
    elif admin_pwd != "":
        st.error("รหัสผ่านไม่ถูกต้อง")

# ----------------- MAIN APP -----------------
if 'last_saved_plate' not in st.session_state:
    st.session_state.last_saved_plate = None
if 'last_saved_province' not in st.session_state:
    st.session_state.last_saved_province = None
if 'last_saved_row' not in st.session_state:
    st.session_state.last_saved_row = None
if 'last_saved_batch' not in st.session_state:
    st.session_state.last_saved_batch = []
if 'last_saved_rows' not in st.session_state:
    st.session_state.last_saved_rows = []

init_vehicle_rows()

# ---- HEADER ----
with st.container(key="parking_header", horizontal=True, horizontal_alignment="distribute", vertical_alignment="top"):
    st.markdown('<div class="parking-brand"><span class="parking-monogram">P</span> NACC PARKING <span class="parking-workspace-label">/ ส่วนงานรักษาความปลอดภัย</span></div><h1 class="parking-title">บันทึกรถค้างอาคาร</h1>', unsafe_allow_html=True)
    render_theme_switch()

with st.container(horizontal=True, key="parking_navigation", gap="xsmall"):
    st.page_link("app_parking.py", label="บันทึกทะเบียน", icon=":material/edit_note:")
    st.page_link("pages/dashboard.py", label="ประวัติ", icon=":material/space_dashboard:")
    st.markdown('<a class="parking-nav" href="#parking-reports">รายงาน <span aria-hidden="true">↗</span></a>', unsafe_allow_html=True)

try:
    sheet = init_connection()
except Exception as e:
    st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {e}")
    st.stop()

with st.container(key="parking_summary_top"):
    home_summary_placeholder = st.empty()
render_home_summary_placeholder(home_summary_placeholder)

with st.container(key="parking_workspace"):
    # ---- FORM SECTION ----
    with st.container(border=True, key="location_panel"):
        st.markdown('<div class="parking-section-heading"><span class="parking-step">01</span><div><h2>สถานที่ตรวจพบ</h2><p>ใช้สถานที่เดียวกันสำหรับทะเบียนในชุดนี้</p></div></div>', unsafe_allow_html=True)
        if not buildings_list:
            st.error("ไม่มีรายชื่ออาคารในระบบ โปรดเพิ่มที่เมนู Admin (แถบด้านซ้าย)")
        if "recording_building" not in st.session_state and st.session_state.get("draft_building") in buildings_list:
            st.session_state.recording_building = st.session_state.draft_building
        building = st.selectbox("อาคาร (Building)", buildings_list if buildings_list else [""], key="recording_building", on_change=remember_building)

    st.markdown('<div class="parking-section-heading"><span class="parking-step">02</span><div><h2>ทะเบียนที่ตรวจพบ</h2><p>กรอกทะเบียนพร้อมจังหวัด เพิ่มได้สูงสุด 100 รายการต่อชุด</p></div></div>', unsafe_allow_html=True)


    provinces_list = ["กรุงเทพมหานคร", "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร", "ขอนแก่น", "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี", "ชัยนาท", "ชัยภูมิ", "ชุมพร", "เชียงราย", "เชียงใหม่", "ตรัง", "ตราด", "ตาก", "นครนายก", "นครปฐม", "นครพนม", "นครราชสีมา", "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", "นราธิวาส", "น่าน", "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์", "ปราจีนบุรี", "ปัตตานี", "พระนครศรีอยุธยา", "พะเยา", "พังงา", "พัทลุง", "พิจิตร", "พิษณุโลก", "เพชรบุรี", "เพชรบูรณ์", "แพร่", "ภูเก็ต", "มหาสารคาม", "มุกดาหาร", "แม่ฮ่องสอน", "ยโสธร", "ยะลา", "ร้อยเอ็ด", "ระนอง", "ระยอง", "ราชบุรี", "ลพบุรี", "ลำปาง", "ลำพูน", "เลย", "ศรีสะเกษ", "สกลนคร", "สงขลา", "สตูล", "สมุทรปราการ", "สมุทรสงคราม", "สมุทรสาคร", "สระแก้ว", "สระบุรี", "สิงห์บุรี", "สุโขทัย", "สุพรรณบุรี", "สุราษฎร์ธานี", "สุรินทร์", "หนองคาย", "หนองบัวลำภู", "อ่างทอง", "อำนาจเจริญ", "อุดรธานี", "อุตรดิตถ์", "อุทัยธานี", "อุบลราชธานี"]

    vehicle_count_key = f"vehicle_count_target_{st.session_state.vehicle_count_widget_version}"
    st.number_input(
        "จำนวนทะเบียนที่จะบันทึก",
        min_value=1,
        max_value=MAX_VEHICLE_ROWS,
        step=1,
        value=len(st.session_state.vehicle_rows),
        key=vehicle_count_key,
        on_change=sync_vehicle_count_to_target,
        args=(vehicle_count_key,),
    )
    with st.container(key="parking_draft_actions"):
        add_col, clear_col = st.columns(2, gap="small")
        with add_col:
            st.button("เพิ่มทะเบียน", icon=":material/add:", width="stretch", on_click=add_vehicle_row)
        with clear_col:
            st.button("ล้างรายการ", width="stretch", on_click=request_clear_vehicle_rows)

    if st.session_state.get("vehicle_row_warning"):
        st.warning(st.session_state.pop("vehicle_row_warning"))

    if st.session_state.get("confirm_clear"):
        st.warning("ล้างทะเบียนที่กำลังกรอกทั้งหมด? รายการที่บันทึกแล้วจะยังอยู่")
        confirm_col, keep_col = st.columns(2)
        with confirm_col:
            st.button("ยืนยันล้างรายการ", on_click=clear_vehicle_rows, key="confirm_clear_button")
        with keep_col:
            if st.button("กรอกต่อ", key="keep_draft"):
                st.session_state.confirm_clear = False
                st.rerun()

    draft_entries, _ = collect_vehicle_entries()
    inline_duplicate_ids = {entry["row_id"] for entry in find_form_duplicates(draft_entries)}
    for display_index, row in enumerate(st.session_state.vehicle_rows, start=1):
        with st.container(border=True, key=f"vehicle_row_{row['id']}"):
            row_id = row["id"]
            st.markdown(f'<div class="parking-row-number">รายการที่ {display_index:02d}</div>', unsafe_allow_html=True)
            col_plate, col_prov, col_delete = st.columns([2.1, 1.6, .65], vertical_alignment="bottom", gap="small")
            with col_plate:
                st.text_input(
                    "ทะเบียนรถยนต์",
                    placeholder="เช่น 9กข 1234",
                    key=f"plate_{row_id}",
                    label_visibility="visible",
                    on_change=remember_vehicle_draft,
                    args=(row_id,),
                )
            with col_prov:
                current_province = st.session_state.get(f"province_{row_id}", DEFAULT_PROVINCE)
                province_index = provinces_list.index(current_province) if current_province in provinces_list else 0
                st.selectbox(
                    "จังหวัด",
                    provinces_list,
                    index=province_index,
                    key=f"province_{row_id}",
                    label_visibility="visible",
                    on_change=remember_vehicle_draft,
                    args=(row_id,),
                )
            with col_delete:
                st.button(
                    "ลบ",
                    help=f"ลบทะเบียนรายการที่ {display_index} ออกจากแบบร่าง",
                    key=f"delete_{row_id}",
                    width="stretch",
                    on_click=delete_vehicle_row,
                    args=(row_id,),
                )

            if row_id in inline_duplicate_ids:
                st.warning("ทะเบียนและจังหวัดซ้ำกับรายการก่อนหน้า กรุณาตรวจสอบ")

    entries_preview, blank_rows = collect_vehicle_entries()
    duplicate_ids = {e["row_id"] for e in find_form_duplicates(entries_preview)}
    if duplicate_ids:
        st.caption("แก้ทะเบียนและจังหวัดที่ซ้ำกันก่อนบันทึก")
    elif not entries_preview:
        st.caption("กรอกทะเบียนอย่างน้อย 1 รายการเพื่อเปิดปุ่มบันทึก")
    else:
        st.caption(f"พร้อมบันทึก {len(entries_preview)} รายการ · {building} · {bangkok_now():%d/%m/%Y}")

    # ---- ACTION BUTTONS ----
    btn_col2 = st.container(key="parking_save_action")

    with btn_col2:
        if st.button("บันทึกข้อมูลเข้าสู่ระบบ", icon=":material/check:", type="primary", width="stretch", disabled=bool(duplicate_ids) or not building or not entries_preview):
            entries, skipped_count = collect_vehicle_entries()
            if not building:
                st.error("❌ กรุณาเลือกอาคารก่อนบันทึกข้อมูลครับ")
            elif not entries:
                st.error("❌ กรุณากรอกทะเบียนรถอย่างน้อย 1 รายการก่อนบันทึกข้อมูลครับ")
            else:
                current_date = bangkok_now().strftime("%Y-%m-%d")

                try:
                    records = read_parking_values(sheet)
                    form_duplicates = find_form_duplicates(entries)
                    sheet_duplicates = find_sheet_duplicates(records, current_date, entries)

                    if form_duplicates or sheet_duplicates:
                        st.error("⚠️ พบรายการซ้ำ จึงยังไม่บันทึกข้อมูลชุดนี้ กรุณาตรวจสอบและแก้ไขก่อน")
                        if form_duplicates:
                            st.warning("รายการซ้ำในฟอร์ม:\n" + format_vehicle_list(form_duplicates))
                        if sheet_duplicates:
                            st.warning("รายการที่มีอยู่แล้วในวันนี้:\n" + format_vehicle_list(sheet_duplicates))
                    else:
                        rows_to_append = [
                            [current_date, building, entry["plate"], entry["province"]]
                            for entry in entries
                        ]
                        with st.spinner("กำลังบันทึกข้อมูล กรุณารอสักครู่"):
                            res = append_parking_rows(sheet, rows_to_append)
                        load_raw_parking_values.clear()
                        clear_dashboard_cache()
                        saved_rows = parse_updated_rows(res, len(rows_to_append))
                        saved_batch = [
                            {
                                "date": current_date,
                                "building": building,
                                "plate": entry["plate"],
                                "province": entry["province"],
                                "record_id": res["record_ids"][index],
                            }
                            for index, entry in enumerate(entries)
                        ]

                        st.session_state.last_saved_batch = saved_batch
                        st.session_state.last_saved_rows = saved_rows
                        st.session_state.last_saved_plate = entries[-1]["plate"]
                        st.session_state.last_saved_province = entries[-1]["province"]
                        st.session_state.last_saved_row = saved_rows[-1] if saved_rows else None

                        st.success(f"บันทึกสำเร็จ {len(rows_to_append)} รายการ · {building} · {bangkok_now():%d/%m/%Y}")
                        st.info("รายการที่บันทึก:\n" + format_vehicle_list(entries))
                        if skipped_count:
                            st.warning(f"ข้ามแถวที่ไม่ได้กรอกทะเบียน {skipped_count} แถว")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")

    if st.session_state.get("last_saved_batch"):
        latest_batch = st.session_state.last_saved_batch
        st.success(f"บันทึกแล้ว {len(latest_batch)} รายการ", icon=":material/check_circle:")
        st.caption(f"ชุดล่าสุด: {len(latest_batch)} รายการ · {latest_batch[0]['building']} · {latest_batch[0]['date']}")
        with st.expander("ดูรายการที่บันทึกล่าสุด", expanded=False):
            st.dataframe(pd.DataFrame([{"ทะเบียนรถ": item["plate"], "จังหวัด": item["province"]} for item in latest_batch]), hide_index=True, width="stretch")

        undo_col2 = st.container(key="parking_cancel_action")
        with undo_col2:
            if st.button("ยกเลิกชุดล่าสุด", icon=":material/undo:", width="content"):
                st.session_state.confirm_cancel = True
            if st.session_state.get("confirm_cancel"):
                st.warning(f"ยกเลิกชุดล่าสุด {len(st.session_state.last_saved_batch)} รายการ?")
                if st.button("เก็บข้อมูลชุดนี้ไว้", key="keep_saved_batch"):
                    st.session_state.confirm_cancel = False
                    st.rerun()
            if st.session_state.get("confirm_cancel") and st.button("ยืนยันยกเลิกชุดล่าสุด", key="confirm_cancel_button"):
                st.session_state.confirm_cancel = False
                saved_batch = st.session_state.last_saved_batch
                saved_rows = st.session_state.get("last_saved_rows", [])

                try:
                    count = cancel_parking_records(sheet, saved_batch)
                    load_raw_parking_values.clear()
                    clear_dashboard_cache()
                    st.warning(f"ยกเลิกข้อมูล {count} รายการแล้ว")
                    st.session_state.last_saved_plate = None
                    st.session_state.last_saved_province = None
                    st.session_state.last_saved_row = None
                    st.session_state.last_saved_batch = []
                    st.session_state.last_saved_rows = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาดในการลบข้อมูล: {e}")

    st.markdown('<div id="parking-reports"></div>', unsafe_allow_html=True)
    with st.expander("ดาวน์โหลดรายงาน CSV / PDF / JPG", expanded=False):
        report_pwd = st.text_input("รหัสผ่านสำหรับโหลดรีพอร์ต:", type="password")
        if report_pwd == "1234":
            report_type = st.selectbox("ประเภทรายงาน", ["รายวัน", "รายสัปดาห์", "รายเดือน"])
            report_date = select_report_date(report_type)
            _, _, report_period_label = get_report_period(report_type, report_date)
            st.caption(f"ช่วงรายงาน: {report_period_label}")
            report_font_options = get_report_font_options()
            report_font_label = st.selectbox("ฟอนต์รายงาน", list(report_font_options.keys()))
            report_font_path = report_font_options[report_font_label]
            if report_font_path and not os.path.exists(report_font_path):
                st.caption(f"ยังไม่พบไฟล์ {report_font_path} ถ้าโหลดตอนนี้ระบบจะใช้ฟอนต์สำรอง")
            report_df = build_detailed_report(load_data(), report_type, report_date)

            if report_df.empty:
                st.info("ไม่พบข้อมูลในช่วงรายงานที่เลือก")
            else:
                st.caption(f"พบรถในรายงาน {len(report_df)} รายการ")
                st.download_button(
                    "⬇️ ดาวน์โหลด CSV รายละเอียด",
                    data=to_csv_bytes(report_df),
                    file_name=make_report_filename(report_type, report_date, "csv"),
                    mime="text/csv",
                    width="stretch",
                )
                st.download_button(
                    "⬇️ ดาวน์โหลด PDF สรุป",
                    data=to_summary_pdf_bytes(
                        report_df,
                        report_df["ช่วงรายงาน"].iloc[0],
                        font_path=report_font_path,
                        report_type=report_type,
                    ),
                    file_name=make_report_filename(report_type, report_date, "pdf"),
                    mime="application/pdf",
                    width="stretch",
                )
                st.download_button(
                    "⬇️ ดาวน์โหลด JPG สรุป",
                    data=to_summary_jpg_bytes(
                        report_df,
                        report_df["ช่วงรายงาน"].iloc[0],
                        font_path=report_font_path,
                        report_type=report_type,
                    ),
                    file_name=make_report_filename(report_type, report_date, "jpg"),
                    mime="image/jpeg",
                    width="stretch",
                )
        elif report_pwd != "":
            st.error("รหัสผ่านไม่ถูกต้อง")



# ---- END OF APP ----
