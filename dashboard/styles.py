from __future__ import annotations

import streamlit as st
from dashboard.theme import apply_theme_css


def apply_dashboard_styles(is_dark: bool = True) -> None:
    apply_theme_css()
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


DASHBOARD_CSS = """
<style>
:root { --dash-text:var(--text); --dash-muted:var(--text-muted); --dash-surface:var(--card-bg); --dash-border:var(--border); --dash-accent:var(--primary); }
.dash-hero { padding:.5rem 0 1.25rem; margin-bottom:.5rem; border-bottom:1px solid var(--border); }
.dash-hero h1 { font-size:1.8rem; line-height:1.5; letter-spacing:-.025em; font-weight:600; padding:0; margin:0; }
.dash-hero p { color:var(--text-muted); font-size:.875rem; margin:.35rem 0 0; }
.dash-sync { color:var(--text-muted); font-size:.75rem; margin-top:.6rem; }
.dash-kpi-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.8rem; margin:.5rem 0 1.5rem; }
.dash-kpi-card,.dash-card { border:1px solid var(--border); border-radius:10px; padding:1.1rem; background:var(--card-bg); box-shadow:var(--card-shadow); min-width:0; }
.dash-kpi-top { display:flex; align-items:center; gap:.5rem; }
.dash-kpi-icon { display:none; }
.dash-kpi-label,.dash-kpi-title { color:var(--text-muted); font-size:.8125rem; }
.dash-kpi-value,.dash-kpi-big { color:var(--text); font-size:clamp(1.25rem,2.5vw,1.8rem); font-weight:500; line-height:1.45; padding:.5rem 0; overflow-wrap:anywhere; font-variant-numeric:tabular-nums; }
.dash-kpi-note,.dash-kpi-caption { color:var(--text-muted); font-size:.75rem; line-height:1.7; }
.dash-section-title { color:var(--text); font-size:1rem; font-weight:600; margin:1.25rem 0 .65rem; }
.dash-filter-title { font-size:.875rem; font-weight:500; color:var(--text); }
.dash-empty { padding:3rem 1.5rem; border:1px dashed var(--border); border-radius:12px; background:var(--card-bg); color:var(--text-muted); text-align:center; line-height:1.8; }
.dash-error { padding:1rem; border:1px solid var(--danger); border-radius:10px; color:var(--danger); }
.dash-timeline-item { padding:.9rem 1rem; border-left:2px solid var(--primary); border-bottom:1px solid var(--border); }
.dash-timeline-meta { color:var(--text-muted); font-size:.8125rem; line-height:1.7; }
[data-testid="stSegmentedControl"] { margin:.5rem 0 1rem; }
@media(max-width:768px) { .dash-kpi-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:.6rem; } .dash-kpi-card,.dash-card { padding:.85rem; } .dash-hero h1 { font-size:1.45rem; } }
</style>
"""
