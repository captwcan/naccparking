from __future__ import annotations

import streamlit as st

THEME_PRESETS: dict[str, dict[str, str]] = {
    "dark": {
        "app_bg": "#0b0f16",
        "sidebar_bg": "#252631",
        "card_bg": "#171b22",
        "card_bg_alt": "#0b2530",
        "text": "#ffffff",
        "text_muted": "#b8c7d9",
        "border": "#303846",
        "primary": "#00a7c8",
        "input_bg": "#282933",
        "button_text": "#06212b",
        "card_shadow": "none",
        "total_border": "rgba(0,167,200,0.5)",
    },
    "light": {
        "app_bg": "#f6f8fb",
        "sidebar_bg": "#f0f2f6",
        "card_bg": "#ffffff",
        "card_bg_alt": "#eaf7fb",
        "text": "#0f172a",
        "text_muted": "#475569",
        "border": "#d7dee8",
        "primary": "#007c99",
        "input_bg": "#ffffff",
        "button_text": "#ffffff",
        "card_shadow": "0 6px 18px rgba(15,23,42,0.06)",
        "total_border": "rgba(44,83,100,0.36)",
    },
}


def init_theme_state() -> None:
    if "ui_theme" not in st.session_state:
        st.session_state.ui_theme = "dark"


def set_theme_from_toggle() -> None:
    st.session_state.ui_theme = "dark" if st.session_state.dark_mode_toggle else "light"


def get_theme() -> dict[str, str]:
    return THEME_PRESETS.get(
        st.session_state.get("ui_theme", "dark"),
        THEME_PRESETS["dark"],
    )


def is_dark_theme() -> bool:
    return st.session_state.get("ui_theme", "dark") == "dark"


def apply_theme_css() -> None:
    t = get_theme()
    variables = ";".join(f"--{name.replace('_', '-')}: {value}" for name, value in t.items())
    st.markdown("<style>:root{" + variables + ";--text-main: var(--text);--border-color: var(--border);--primary-color: var(--primary);}</style>" + SHARED_CSS, unsafe_allow_html=True)


SHARED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600;700&display=swap');
html, body, .stApp, input, textarea, button, select { font-family: 'Noto Sans Thai', sans-serif; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--app-bg) !important; color: var(--text) !important; }
[data-testid="stMainBlockContainer"] { max-width: 1120px; padding: 1.6rem 2rem 3rem; }
[data-testid="stSidebar"] { background: var(--sidebar-bg) !important; }
h1,h2,h3,h4,h5,h6,p,label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] { color: var(--text) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--text-muted) !important; }
input, textarea, [data-baseweb="select"] > div, [data-baseweb="popover"] [role="listbox"] { background: var(--input-bg) !important; color: var(--text) !important; border-color: var(--border) !important; }
[role="option"] { color: var(--text) !important; background: var(--input-bg); }
input::placeholder, textarea::placeholder { color: var(--text-muted); opacity: .8; }
button { min-height: 44px; border-radius: 10px !important; color: var(--text) !important; }
button[kind="primary"], [data-testid="stBaseButton-primary"] { background: var(--primary) !important; border-color: var(--primary) !important; color: var(--button-text) !important; font-weight: 600; }
button[kind="primary"] p { color: var(--button-text) !important; }
button:focus-visible, input:focus-visible, a:focus-visible { outline: 3px solid var(--primary) !important; outline-offset: 3px; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color: var(--border) !important; }
.section-title { font-size: 1.05rem; font-weight: 650; color: var(--text) !important; margin: .9rem 0 .5rem; }
.parking-header { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:.6rem; margin:0 0 .6rem; }
.parking-brand { font-size:.75rem; font-weight:700; letter-spacing:.13em; color:var(--primary); }
.parking-title { font-size:clamp(1.35rem, 3.5vw, 2rem); font-weight:700; line-height:1.5; color:var(--text); }
.parking-date { font-size:.85rem; color:var(--text-muted); }
.parking-summary { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.85rem 1rem; border:1px solid var(--border); border-radius:12px; background:var(--card-bg); color:var(--text); }
.parking-summary strong { font-size:1.45rem; color:var(--primary); }
.parking-summary small { color:var(--text-muted); }
.parking-nav { display:inline-block; padding:.5rem .75rem; color:var(--primary) !important; text-decoration:none; border-radius:8px; }
.mini-dashboard-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.65rem; }
.mini-stat-card { background:var(--card-bg); border:1px solid var(--border); border-radius:10px; padding:.8rem; min-width:0; }
.mini-stat-top { display:flex; align-items:center; gap:.5rem; }
.mini-stat-icon { color:var(--primary); }
.mini-stat-title, .mini-stat-subtitle { color:var(--text-muted); font-size:.8rem; overflow-wrap:anywhere; }
.mini-stat-value { color:var(--text); font-size:1.5rem; font-weight:650; margin:.3rem 0; }
.mini-stat-card--total { border-color:var(--primary); }
div[class*="st-key-vehicle_row_"] { background:var(--card-bg); border-radius:12px; }
div[class*="st-key-vehicle_row_"] [data-testid="stHorizontalBlock"] { align-items:end; }
.dash-hero { padding:1rem !important; margin-bottom:.8rem !important; }
.dash-hero h1 { font-size:1.65rem !important; }
.dash-kpi-card, .dash-card { min-height:0 !important; }
@media(max-width:640px) {
 [data-testid="stMainBlockContainer"] { padding:1rem .9rem 2rem; }
 .parking-title { font-size:1.3rem; }
 .mini-dashboard-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
 .parking-summary { align-items:start; }
 .dash-kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)) !important; }
 div[class*="st-key-vehicle_row_"] [data-testid="stHorizontalBlock"] { flex-wrap:wrap; gap:.5rem; }
 div[class*="st-key-vehicle_row_"] [data-testid="stColumn"] { min-width:0 !important; flex:1 1 100% !important; width:100% !important; }
}
</style>
"""
