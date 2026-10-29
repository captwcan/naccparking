from __future__ import annotations

import streamlit as st

THEME_PRESETS = {
    "dark": {
        "app_bg": "#101419", "sidebar_bg": "#12171e",
        "card_bg": "#191f27", "card_bg_alt": "#202933",
        "text": "#edf1f7", "text_muted": "#a5afbf",
        "border": "#35404e", "primary": "#8cd4c3",
        "input_bg": "#131920", "button_text": "#102d27",
        "card_shadow": "0 8px 24px rgba(0,0,0,.10)",
        "total_border": "#42655d", "danger": "#ffaaa8",
    },
    "light": {
        "app_bg": "#f5f6f8", "sidebar_bg": "#eff1f4",
        "card_bg": "#ffffff", "card_bg_alt": "#edf3f1",
        "text": "#202b3a", "text_muted": "#5c6879",
        "border": "#ccd3dc", "primary": "#126b5b",
        "input_bg": "#ffffff", "button_text": "#ffffff",
        "card_shadow": "0 4px 20px rgba(31,43,58,.04)",
        "total_border": "#c4d8d1", "danger": "#b42329",
    },
}


def init_theme_state():
    if "ui_theme" not in st.session_state:
        st.session_state.ui_theme = "dark"


def set_theme_from_toggle():
    st.session_state.ui_theme = "dark" if st.session_state.dark_mode_toggle else "light"


def get_theme():
    return THEME_PRESETS.get(st.session_state.get("ui_theme", "dark"), THEME_PRESETS["dark"])


def is_dark_theme():
    return st.session_state.get("ui_theme", "dark") == "dark"


def apply_theme_css():
    variables = ";".join(f"--{k.replace('_', '-')}: {v}" for k, v in get_theme().items())
    st.markdown("<style>:root{" + variables + ";--text-main:var(--text);--border-color:var(--border);--primary-color:var(--primary);}</style>" + SHARED_CSS, unsafe_allow_html=True)


SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;450;500;600&display=swap');
html,body,input,textarea,button,select { font-family:'IBM Plex Sans Thai',sans-serif; }
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { background:var(--app-bg) !important; color:var(--text) !important; }
[data-testid="stMainBlockContainer"] { max-width:1040px; padding:3.5rem 2rem 3rem; }
[data-testid="stHeader"] { background:var(--app-bg) !important; }
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
[data-testid="stSelectbox"] [role="group"] { background:var(--input-bg) !important; color:var(--text) !important; border-color:var(--border) !important; }
button[kind="secondary"],[data-testid="stBaseButton-secondary"] { background:var(--card-bg) !important; border:1px solid var(--border) !important; color:var(--text) !important; }
button[kind="secondary"]:hover { background:var(--card-bg-alt) !important; border-color:var(--text-muted) !important; }
button[kind="primary"],[data-testid="stBaseButton-primary"] { background:var(--primary) !important; color:var(--button-text) !important; border:1px solid var(--primary) !important; font-weight:600; }
button[kind="primary"]:hover:not(:disabled) { filter:brightness(.95); }
button[kind="primary"] p,button[kind="secondary"] p { color:inherit !important; }
button[kind="primary"]:disabled { opacity:.45; cursor:not-allowed; }
[data-testid="stButton"] button { min-height:44px; border-radius:8px; padding:.55rem .9rem; }
button:focus-visible,input:focus-visible,a:focus-visible { outline:3px solid var(--primary) !important; outline-offset:3px; }
[data-testid="stExpander"] { border-color:var(--border); border-radius:10px; background:var(--card-bg); }
[data-testid="stExpander"] summary { min-height:44px; color:var(--text); }
[data-testid="stExpander"] summary p { color:var(--text); font-size:.875rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--border) !important; }
.parking-brand { display:flex; align-items:center; gap:.6rem; font-size:.72rem; letter-spacing:.09em; font-weight:600; color:var(--text-muted); }
.parking-monogram { display:inline-grid; place-items:center; width:28px; height:28px; border:1px solid var(--border); border-radius:7px; font-size:1rem; color:var(--primary); letter-spacing:0; }
.parking-workspace-label { font-weight:400; letter-spacing:0; }
.parking-title { font-size:clamp(1.5rem,2.6vw,1.9rem) !important; font-weight:600; line-height:1.5; padding:.6rem 0 .2rem !important; margin:0; letter-spacing:-.025em; }
.parking-subtitle { color:var(--text-muted); font-size:.875rem; line-height:1.7; }
.st-key-parking_navigation { padding:.2rem 0 1.1rem; border-bottom:1px solid var(--border); margin-bottom:1rem; }
.st-key-parking_navigation [data-testid="stPageLink"] a,.parking-nav { display:flex; align-items:center; gap:.45rem; min-height:44px; padding:.55rem .85rem; color:var(--text-muted) !important; font-size:.875rem; text-decoration:none; border-radius:8px; }
.st-key-parking_navigation [data-testid="stPageLink"] a[aria-current="page"] { background:var(--card-bg-alt); color:var(--text) !important; }
.st-key-parking_navigation [data-testid="stPageLink"] a:hover,.parking-nav:hover { background:var(--card-bg-alt); color:var(--text) !important; }
.parking-section-heading { display:flex; align-items:flex-start; gap:.75rem; margin:.35rem 0 .7rem; }
.parking-step { color:var(--primary); font-size:.75rem; font-weight:600; border:1px solid var(--border); border-radius:7px; padding:.3rem .45rem; margin-top:.1rem; font-variant-numeric:tabular-nums; }
.parking-section-heading h2 { font-size:1rem !important; font-weight:600; margin:0; padding:0 !important; }
.parking-section-heading p { color:var(--text-muted) !important; font-size:.8125rem; margin:.2rem 0 0; line-height:1.7; }
.st-key-location_panel { background:var(--card-bg); border-color:var(--border) !important; border-radius:12px; padding:1.15rem !important; box-shadow:var(--card-shadow); margin-bottom:.5rem; }
div[class*="st-key-vehicle_row_"] { background:var(--card-bg); border-color:var(--border) !important; border-radius:10px; padding:.85rem 1rem !important; }
.parking-row-number { color:var(--text-muted); font-size:.75rem; font-weight:500; }
div[class*="st-key-vehicle_row_"] [data-testid="stTextInput"] input { letter-spacing:.035em; }
div[class*="st-key-vehicle_row_"] [data-testid="stButton"] button { color:var(--text-muted) !important; }
.st-key-parking_save_action { border-top:1px solid var(--border); padding-top:1rem; }
.st-key-parking_cancel_action [data-testid="stButton"] button { color:var(--danger) !important; }
.st-key-parking_summary_panel { padding:1rem !important; border-color:var(--border) !important; border-radius:14px; background:var(--card-bg); box-shadow:var(--card-shadow); }
.mini-dashboard-shell { padding:0; }
.mini-dashboard-heading { display:flex; align-items:center; justify-content:space-between; gap:.5rem; margin-bottom:.8rem; }
.mini-dashboard-heading h2 { font-size:.95rem !important; padding:0 !important; margin:0; font-weight:600; }
.summary-business-date { color:var(--text-muted); font-size:.75rem; font-variant-numeric:tabular-nums; }
.mini-dashboard-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:.65rem; }
.mini-stat-card { position:relative; min-width:0; border:1px solid var(--border); border-radius:10px; background:var(--input-bg); padding:.8rem; overflow:hidden; }
.mini-stat-top { min-height:1.6rem; line-height:1.5; }
.mini-stat-title { font-size:.75rem; color:var(--text-muted); overflow-wrap:anywhere; }
.mini-stat-reading { display:flex; align-items:center; gap:.4rem; margin:.2rem 0; }
.mini-stat-value { font-size:1.8rem; font-weight:500; line-height:1.3; color:var(--text); font-variant-numeric:tabular-nums; letter-spacing:-.035em; }
.mini-stat-subtitle { display:block; color:var(--text-muted); font-size:.65rem; }
.mini-stat-card--total { background:var(--card-bg-alt); border-color:var(--total-border); box-shadow:inset 0 3px 0 var(--primary); }
.mini-stat-card--total .mini-stat-title,.mini-stat-card--total .mini-stat-value { color:var(--primary); }
.mini-stat-delta { font-size:.7rem; font-weight:500; color:var(--primary); border-radius:5px; background:var(--card-bg-alt); padding:.1rem .25rem; }
.mini-stat-card--updated { border-color:var(--primary); }
.mini-stat-card--updated .mini-stat-value { animation:summary-number-in .3s ease-out; }
.summary-freshness { display:flex; align-items:center; gap:.4rem; color:var(--text-muted); font-size:.7rem; margin-top:.75rem; }
.summary-status-dot { width:6px; height:6px; background:var(--primary); border-radius:50%; flex-shrink:0; }
.summary-change-announcement:empty { display:none; }
.summary-change-announcement { font-size:.75rem; color:var(--primary); margin-top:.4rem; }
.mini-dashboard-error { color:var(--danger); border:1px solid var(--danger); border-radius:10px; padding:1rem; }
.st-key-parking_summary_refresh { margin-top:0; }
.st-key-parking_summary_refresh button { font-size:.75rem; min-height:36px; padding:.25rem .6rem; }
.st-key-parking_workspace { max-width:820px; margin:0 auto; width:100%; }
@keyframes summary-number-in { from { opacity:.4; transform:translateY(5px); } to { opacity:1; transform:translateY(0); } }
@media(min-width:900px) { .st-key-parking_workspace > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child { position:sticky; top:4rem; align-self:flex-start; } }
@media(max-width:768px) {
 [data-testid="stMainBlockContainer"] { padding:3.5rem 1rem 2rem; }
 .parking-workspace-label { display:none; }
 .parking-title { font-size:1.45rem !important; }
 .st-key-parking_navigation { margin-bottom:.5rem; }
 .st-key-parking_navigation [data-testid="stPageLink"] a,.parking-nav { padding:.5rem .65rem; font-size:.8125rem; }
 .st-key-location_panel { padding:1rem !important; }
 div[class*="st-key-vehicle_row_"] { padding:.85rem !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.6rem; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"] { min-width:0 !important; flex:1 1 100% !important; width:100% !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"]:last-child { flex:0 1 auto !important; width:auto !important; margin-left:auto; }
 .st-key-parking_summary_panel { padding:.85rem !important; }
 .mini-dashboard-grid { grid-template-columns:repeat(3,minmax(0,1fr)); gap:.5rem; }
 .mini-stat-card { padding:.65rem .6rem; }
 .mini-stat-top { min-height:1.6rem; }
 .mini-stat-value { font-size:1.65rem; }
 .mini-stat-title { font-size:.72rem; }
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
