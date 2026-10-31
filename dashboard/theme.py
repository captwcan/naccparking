from __future__ import annotations

from pathlib import Path

import streamlit as st

THEME_PRESETS = {
    "dark": {
        "app_bg": "#111015", "sidebar_bg": "#16141c",
        "card_bg": "#1d1b25", "card_bg_alt": "#2a2538",
        "text": "#f2eff8", "text_muted": "#b2aabe",
        "border": "#4d455d", "primary": "#bda3ff",
        "input_bg": "#17151e", "button_text": "#201333",
        "card_shadow": "0 10px 30px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.025)",
        "total_border": "#8266a9", "danger": "#ffb1b5",
        "card_gradient": "linear-gradient(160deg,#24212e 0%,#1d1b25 80%)",
        "summary_gradient": "linear-gradient(135deg,#292332 0%,#1e1b27 62%,#1c1923 100%)",
        "total_gradient": "linear-gradient(145deg,#51406f 0%,#35294b 60%,#292237 100%)",
        "button_gradient": "linear-gradient(110deg,#c7b1ff 0%,#ac8be9 100%)",
        "accent_soft": "#30263f", "total_text": "#eee4ff",
        "status": "#8bd3b3", "decoration": "#c5a7ff",
    },
    "light": {
        "app_bg": "#f5f2f9", "sidebar_bg": "#eee9f4",
        "card_bg": "#ffffff", "card_bg_alt": "#eee7f8",
        "text": "#2b2436", "text_muted": "#70657e",
        "border": "#b5aac5", "primary": "#7042b5",
        "input_bg": "#fcfaff", "button_text": "#ffffff",
        "card_shadow": "0 8px 24px rgba(52,34,78,.045), inset 0 1px 0 #fff",
        "total_border": "#b49bd5", "danger": "#b42339",
        "card_gradient": "linear-gradient(160deg,#ffffff 30%,#fbf8ff 100%)",
        "summary_gradient": "linear-gradient(135deg,#ffffff 20%,#f5effd 100%)",
        "total_gradient": "linear-gradient(145deg,#eee2ff 0%,#e9ddfa 70%,#e1d2f5 100%)",
        "button_gradient": "linear-gradient(110deg,#7548bd 0%,#5f349e 100%)",
        "accent_soft": "#eee5fc", "total_text": "#532b86",
        "status": "#257457", "decoration": "#9772c5",
    },
}


def init_theme_state():
    if "ui_theme" not in st.session_state:
        st.session_state.ui_theme = "dark"


def toggle_theme():
    st.session_state.ui_theme = "light" if is_dark_theme() else "dark"


def render_theme_switch():
    dark = is_dark_theme()
    st.button(
        "สว่าง" if dark else "มืด",
        icon=":material/light_mode:" if dark else ":material/dark_mode:",
        help="เปลี่ยนเป็นโหมดสว่าง" if dark else "เปลี่ยนเป็นโหมดมืด",
        key="parking_theme_toggle",
        on_click=toggle_theme,
        width="content",
    )


def get_theme():
    return THEME_PRESETS.get(st.session_state.get("ui_theme", "dark"), THEME_PRESETS["dark"])


def is_dark_theme():
    return st.session_state.get("ui_theme", "dark") == "dark"


def apply_theme_css():
    variables = ";".join(f"--{k.replace('_', '-')}: {v}" for k, v in get_theme().items())
    st.markdown("<style>:root{" + variables + ";--text-main:var(--text);--border-color:var(--border);--primary-color:var(--primary);}</style>" + SHARED_CSS, unsafe_allow_html=True)
    # Use the native client theme as well as the app's layout tokens. Canvas
    # tables and calendar popovers cannot be themed reliably with CSS alone.
    script = Path(__file__).with_name("theme_sync.js").read_text(encoding="utf-8")
    script = script.replace("__PARKING_THEME__", "dark" if is_dark_theme() else "light")
    st.html(f"<script>{script}</script>", unsafe_allow_javascript=True)


SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;450;500;600&display=swap');
html,body,input,textarea,button,select { font-family:'IBM Plex Sans Thai',sans-serif; }
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { background:var(--app-bg) !important; color:var(--text) !important; }
[data-testid="stMainBlockContainer"] { max-width:1040px; padding:3.5rem 2rem 3rem; }
[data-testid="stHeader"] { background:var(--app-bg) !important; }
.parking-theme-sync [data-testid="stMainMenuPopover"] { visibility:hidden !important; }
[data-testid="stThemeSwitcher"] { display:none; }
.st-key-parking_header { flex-wrap:nowrap !important; align-items:flex-start !important; gap:.75rem !important; }
.st-key-parking_header > [data-testid="stElementContainer"]:first-child { flex:1 1 0%; min-width:0; }
.st-key-parking_header > [data-testid="stElementContainer"]:last-child { flex:0 0 auto; }
.st-key-parking_theme_toggle button { min-height:44px; white-space:nowrap; border-radius:999px !important; font-size:.8125rem; }
[data-testid="stSidebar"] { background:var(--sidebar-bg) !important; border-right:1px solid var(--border); }
[data-testid="stSidebar"] h2 { font-size:1rem; }
h1,h2,h3,h4,h5,h6,[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"] { color:var(--text) !important; }
[data-testid="stWidgetLabel"] p { font-size:.875rem; font-weight:500; color:var(--text); }
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p { color:var(--text-muted) !important; font-size:.8125rem; }
input,textarea { color:var(--text) !important; background:var(--input-bg) !important; font-size:1rem !important; }
input::placeholder,textarea::placeholder { color:var(--text-muted) !important; -webkit-text-fill-color:var(--text-muted) !important; opacity:1; }
[data-testid="stNumberInput"] button { color:var(--text) !important; background:var(--input-bg) !important; }
[data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div { background:var(--input-bg); border-color:var(--border); border-radius:8px; }
[role="listbox"],[role="option"],[data-baseweb="popover"] { background:var(--card-bg) !important; color:var(--text) !important; }
[role="option"]:hover,[role="option"][aria-selected="true"] { background:var(--card-bg-alt) !important; }
[data-testid="stSelectbox"] button,[data-testid="stSelectbox"] [role="combobox"],
[data-testid="stSelectbox"] [role="group"],
[data-testid="stMultiSelect"] button,[data-testid="stMultiSelect"] [role="group"],
[data-testid="stDateInput"] > div,[data-testid="stDateInputField"],
[data-testid="stDateInputCalendarButton"] { background:var(--input-bg) !important; color:var(--text) !important; border-color:var(--border) !important; }
[data-testid="stDateInputField"] span { color:var(--text) !important; }
button[kind="secondary"],[data-testid="stBaseButton-secondary"] { background:var(--card-bg) !important; border:1px solid var(--border) !important; color:var(--text) !important; }
button[kind="secondary"]:hover { background:var(--card-bg-alt) !important; border-color:var(--text-muted) !important; }
button[kind="primary"],[data-testid="stBaseButton-primary"] { background:var(--button-gradient) !important; color:var(--button-text) !important; border:1px solid transparent !important; font-weight:600; box-shadow:0 4px 14px color-mix(in srgb,var(--primary) 14%,transparent); }
button[kind="primary"]:hover:not(:disabled) { filter:brightness(.95); }
button[kind="primary"] *,button[kind="secondary"] * { color:inherit !important; }
button[kind="primary"]:disabled { opacity:.45; cursor:not-allowed; }
[data-testid="stButton"] button { min-height:44px; border-radius:10px; padding:.55rem .9rem; transition:background .18s ease,border-color .18s ease,box-shadow .18s ease; }
[data-testid="stButtonGroup"] [data-variant="segmented_control"] { min-height:44px; background:var(--card-bg) !important; color:var(--text) !important; border-color:var(--border) !important; }
[data-testid="stButtonGroup"] [data-variant="segmented_control"] [data-testid="stMarkdownContainer"] { color:inherit !important; }
[data-testid="stButtonGroup"] [data-variant="segmented_control"]:hover { background:var(--card-bg-alt) !important; }
[data-testid="stButtonGroup"] [data-variant="segmented_control"][data-selected] { background:var(--card-bg-alt) !important; border-color:var(--primary) !important; box-shadow:inset 0 -2px 0 var(--primary); }
button:focus-visible,input:focus-visible,a:focus-visible { outline:3px solid var(--primary) !important; outline-offset:3px; }
[data-testid="stExpander"] { border-color:var(--border); border-radius:10px; background:var(--card-bg); }
[data-testid="stExpander"] summary { min-height:44px; color:var(--text); }
[data-testid="stExpander"] summary p { color:var(--text); font-size:.875rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--border) !important; }
.parking-brand { display:flex; align-items:center; gap:.6rem; font-size:.7rem; letter-spacing:.12em; font-weight:600; color:var(--text-muted); }
.parking-monogram { display:inline-grid; place-items:center; width:28px; height:28px; border:1px solid var(--total-border); border-radius:9px; background:var(--accent-soft); font-size:1rem; color:var(--primary); letter-spacing:0; box-shadow:inset 0 1px 0 color-mix(in srgb,var(--primary) 14%,transparent); }
.parking-workspace-label { font-weight:400; letter-spacing:0; }
.parking-title { font-size:clamp(1.5rem,2.6vw,1.9rem) !important; font-weight:600; line-height:1.5; padding:.55rem 0 .2rem !important; margin:0; letter-spacing:-.035em; }
.parking-subtitle { color:var(--text-muted); font-size:.875rem; line-height:1.7; }
.st-key-parking_navigation { padding:.25rem 0 .9rem; border-bottom:1px solid color-mix(in srgb,var(--border) 55%,transparent); margin-bottom:.75rem; gap:.25rem !important; }
.st-key-parking_navigation [data-testid="stPageLink"] a,.parking-nav { display:flex; align-items:center; gap:.45rem; min-height:44px; padding:.55rem .85rem; color:var(--text-muted) !important; font-size:.875rem; text-decoration:none; border-radius:10px; }
.st-key-parking_navigation_current [data-testid="stPageLink"] a { background:var(--accent-soft); color:var(--primary) !important; box-shadow:inset 0 -2px 0 var(--primary); }
.st-key-parking_navigation [data-testid="stPageLink"] a * { color:inherit !important; }
.st-key-parking_navigation [data-testid="stPageLink"] a:hover,.parking-nav:hover { background:var(--card-bg-alt); color:var(--text) !important; }
.parking-section-heading { display:flex; align-items:flex-start; gap:.75rem; margin:.35rem 0 .7rem; }
.parking-step { color:var(--primary); background:var(--accent-soft); font-size:.7rem; font-weight:600; border:1px solid color-mix(in srgb,var(--primary) 25%,transparent); border-radius:50%; width:28px; height:28px; display:inline-grid; place-items:center; flex-shrink:0; margin-top:.1rem; font-variant-numeric:tabular-nums; }
.parking-section-heading h2 { font-size:1rem !important; font-weight:600; margin:0; padding:0 !important; }
.parking-section-heading p { color:var(--text-muted) !important; font-size:.8125rem; margin:.2rem 0 0; line-height:1.7; }
.st-key-location_panel { background:var(--card-gradient); border-color:color-mix(in srgb,var(--border) 65%,transparent) !important; border-radius:16px; padding:1.15rem !important; box-shadow:var(--card-shadow); margin-bottom:.5rem; }
div[class*="st-key-vehicle_row_"] { background:var(--card-gradient); border-color:color-mix(in srgb,var(--border) 65%,transparent) !important; border-radius:14px; padding:.85rem 1rem !important; }
.parking-row-number { color:var(--text-muted); font-size:.75rem; font-weight:500; }
div[class*="st-key-vehicle_row_"] [data-testid="stTextInput"] input { letter-spacing:.035em; }
div[class*="st-key-vehicle_row_"] [data-testid="stButton"] button { color:var(--text-muted) !important; }
.st-key-parking_save_action { border-top:1px solid var(--border); padding-top:1rem; }
.st-key-parking_save_action button { min-height:50px; }
.st-key-parking_draft_actions [data-testid="stColumn"]:first-child button { background:var(--accent-soft) !important; color:var(--primary) !important; border-color:var(--total-border) !important; }
.st-key-parking_cancel_action [data-testid="stButton"] button { color:var(--danger) !important; }
.st-key-parking_summary_panel { padding:1.1rem !important; border-color:color-mix(in srgb,var(--total-border) 60%,transparent) !important; border-radius:20px; background:var(--summary-gradient); box-shadow:var(--card-shadow); }
.mini-dashboard-shell { padding:0; }
.mini-dashboard-heading { display:flex; align-items:center; justify-content:space-between; gap:.5rem; margin-bottom:.9rem; }
.mini-dashboard-heading h2 { font-size:1rem !important; padding:0 !important; margin:0; font-weight:600; letter-spacing:-.02em; }
.summary-business-date { color:var(--text-muted); font-size:.75rem; font-variant-numeric:tabular-nums; }
.mini-dashboard-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.5rem; }
.mini-stat-card { position:relative; min-width:0; border:1px solid transparent; border-radius:12px; background:color-mix(in srgb,var(--input-bg) 55%,transparent); padding:.85rem; overflow:hidden; box-shadow:inset 0 1px 0 color-mix(in srgb,var(--border) 35%,transparent); }
.mini-stat-top { min-height:1.6rem; line-height:1.5; }
.mini-stat-title { font-size:.75rem; color:var(--text-muted); overflow-wrap:anywhere; }
.mini-stat-reading { display:flex; flex-wrap:wrap; align-items:center; gap:.35rem; margin:.35rem 0 .15rem; }
.mini-stat-value { font-size:2.2rem; font-weight:500; line-height:1.2; color:var(--text); font-variant-numeric:tabular-nums; letter-spacing:-.05em; }
.mini-stat-subtitle { display:block; color:var(--text-muted); font-size:.7rem; }
.mini-stat-card--total { background:var(--total-gradient); border-color:var(--total-border); box-shadow:inset 0 1px 0 color-mix(in srgb,var(--decoration) 22%,transparent); }
.mini-stat-card--total::after { content:""; position:absolute; width:72px; height:72px; right:-40px; bottom:-42px; border:1px solid var(--decoration); border-radius:50%; box-shadow:0 0 0 10px color-mix(in srgb,var(--decoration) 13%,transparent),0 0 0 20px color-mix(in srgb,var(--decoration) 7%,transparent); opacity:.45; pointer-events:none; }
.mini-stat-card--total .mini-stat-title,.mini-stat-card--total .mini-stat-value { color:var(--total-text); }
.mini-stat-card--total .mini-stat-subtitle { color:var(--total-text); opacity:.85; }
.mini-stat-delta { font-size:.7rem; font-weight:500; color:var(--primary); border-radius:5px; background:var(--card-bg-alt); padding:.1rem .25rem; }
.mini-stat-card--updated { border-color:var(--primary); }
.mini-stat-card--updated .mini-stat-value { animation:summary-number-in .3s ease-out; }
.summary-freshness { display:flex; align-items:center; gap:.4rem; color:var(--text-muted); font-size:.75rem; margin-top:.85rem; }
.summary-status-dot { width:5px; height:5px; background:var(--status); border-radius:50%; flex-shrink:0; }
.summary-change-announcement:empty { display:none; }
.summary-change-announcement { font-size:.75rem; color:var(--primary); margin-top:.4rem; }
.mini-dashboard-error { color:var(--danger); border:1px solid var(--danger); border-radius:10px; padding:1rem; }
.st-key-parking_summary_refresh { margin-top:0; }
.st-key-parking_summary_refresh button { font-size:.75rem; min-height:44px; padding:.35rem .65rem; border-radius:999px; }
.st-key-parking_workspace { max-width:820px; margin:0 auto; width:100%; }
@keyframes summary-number-in { from { opacity:.4; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }
@media(min-width:900px) { .st-key-parking_workspace > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child { position:sticky; top:4rem; align-self:flex-start; } }
@media(max-width:768px) {
 [data-testid="stMainBlockContainer"] { padding:3.5rem 1rem 2rem; }
 [data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],[data-testid="stSelectbox"] [role="group"] { min-height:46px; }
 [data-testid="stTextInput"] input,[data-testid="stSelectbox"] [role="combobox"] { min-height:44px; }
 .parking-workspace-label { display:none; }
 .parking-title { font-size:1.45rem !important; }
 .st-key-parking_navigation { margin-bottom:.5rem; }
 .st-key-parking_navigation [data-testid="stPageLink"] a,.parking-nav { padding:.5rem .65rem; font-size:.8125rem; }
 .st-key-location_panel { padding:1rem !important; }
 div[class*="st-key-vehicle_row_"] { padding:.85rem !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.6rem; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"] { min-width:0 !important; flex:1 1 100% !important; width:100% !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"]:last-child { flex:0 1 auto !important; width:auto !important; margin-left:auto; }
 .st-key-parking_summary_panel { padding:.9rem !important; }
 .mini-dashboard-grid { grid-template-columns:repeat(3,minmax(0,1fr)); gap:.5rem; }
 .mini-stat-card { padding:.7rem .55rem .65rem; }
 .mini-stat-top { min-height:1.6rem; }
 .mini-stat-value { font-size:1.95rem; }
 .mini-stat-title { font-size:.75rem; }
 .mini-stat-card:not(.mini-stat-card--total) .mini-stat-subtitle { display:none; }
 .parking-section-heading p { display:none; }
 .st-key-parking_navigation { padding-bottom:.55rem; }
 .st-key-parking_workspace { margin:0; }
 .st-key-location_panel { padding:.75rem !important; }
}
/* Keep each vehicle as one compact row, including on narrow phones. */
@media(max-width:768px) {
 .st-key-parking_draft_actions [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.65rem !important; }
 .st-key-parking_draft_actions [data-testid="stColumn"] { flex:1 1 0% !important; width:0 !important; min-width:0 !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:.45rem !important; align-items:flex-end; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"]:nth-child(1) { flex:1.6 1 0% !important; width:0 !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"]:nth-child(2) { flex:1.45 1 0% !important; width:0 !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"]:last-child { flex:0 0 44px !important; width:44px !important; margin-left:0; }
 div[class*="st-key-vehicle_row_"] [data-testid="stButton"] button { padding:.4rem .25rem; width:44px; min-width:44px; }
 div[class*="st-key-vehicle_row_"] [data-testid="stWidgetLabel"] p { font-size:.8rem; }
 div[class*="st-key-vehicle_row_"] { padding:.7rem !important; }
}
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { scroll-behavior:auto !important; transition:none !important; animation:none !important; } }
</style>
"""
