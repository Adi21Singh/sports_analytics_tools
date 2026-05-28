"""Single source of truth for all injected CSS."""

import streamlit as st
from config import COLORS


_CSS = f"""
<style>

/* ── Layout ──────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"]  {{ background:{COLORS['bg']}; }}
[data-testid="stSidebar"]           {{ background:{COLORS['surface']}; border-right:1px solid {COLORS['border']}; }}
section.main > div                  {{ padding-top:1.2rem; }}

/* ── Typography ──────────────────────────────────────────────── */
h1,h2,h3,h4 {{ color:{COLORS['text']}; font-weight:700; }}
p, li        {{ color:{COLORS['muted']}; line-height:1.6; }}
label        {{ color:{COLORS['muted']} !important; font-size:0.8rem; }}

/* ── Tabs ────────────────────────────────────────────────────── */
[data-testid="stTabs"] button {{
    color: {COLORS['muted']};
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    border-radius: 8px 8px 0 0;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color: {COLORS['primary']};
    border-bottom: 2px solid {COLORS['primary']};
}}

/* ── Divider ─────────────────────────────────────────────────── */
hr {{ border-color: {COLORS['border']}; margin: 1.4rem 0; }}

/* ── KPI card ────────────────────────────────────────────────── */
.kpi-card {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    position: relative;
    overflow: hidden;
}}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, {COLORS['primary']});
    border-radius: 14px 14px 0 0;
}}
.kpi-label   {{ font-size:0.72rem; color:{COLORS['muted']}; text-transform:uppercase; letter-spacing:.06em; margin-bottom:.35rem; }}
.kpi-value   {{ font-size:2rem;    font-weight:700; color:{COLORS['text']}; line-height:1.1; }}
.kpi-delta   {{ font-size:0.78rem; margin-top:.3rem; }}
.delta-pos   {{ color:{COLORS['success']}; }}
.delta-neg   {{ color:{COLORS['danger']};  }}
.delta-neu   {{ color:{COLORS['muted']};   }}
.kpi-sub     {{ font-size:0.78rem; color:{COLORS['muted']}; margin-top:.25rem; }}

/* ── Section header ──────────────────────────────────────────── */
.section-header {{
    display:flex; align-items:center; gap:.6rem;
    margin: 1.4rem 0 .8rem;
    padding-bottom: .6rem;
    border-bottom: 1px solid {COLORS['border']};
}}
.section-header h3 {{
    margin:0; font-size:1.05rem;
    color:{COLORS['text']};
}}
.section-sub {{ font-size:.8rem; color:{COLORS['muted']}; margin:.2rem 0 0; }}

/* ── Risk badges ─────────────────────────────────────────────── */
.badge {{
    display:inline-block; border-radius:20px; padding:.2rem .75rem;
    font-size:.75rem; font-weight:600; letter-spacing:.04em;
}}
.badge-optimal  {{ background:#0d3324; color:{COLORS['success']}; border:1px solid {COLORS['success']}44; }}
.badge-caution  {{ background:#3a2800; color:{COLORS['warning']}; border:1px solid {COLORS['warning']}44; }}
.badge-high     {{ background:#3a0d0d; color:{COLORS['danger']};  border:1px solid {COLORS['danger']}44;  }}
.badge-under    {{ background:#1a1a36; color:{COLORS['secondary']};border:1px solid {COLORS['secondary']}44; }}

/* ── Info box ────────────────────────────────────────────────── */
.info-box {{
    background:{COLORS['surface_alt']};
    border-left: 3px solid {COLORS['primary']};
    border-radius: 0 8px 8px 0;
    padding: .75rem 1rem;
    margin: .8rem 0;
    font-size:.84rem;
    color:{COLORS['muted']};
}}

/* ── Sidebar player card ──────────────────────────────────────── */
.player-card {{
    background:{COLORS['surface_alt']};
    border:1px solid {COLORS['border']};
    border-radius:12px;
    padding:.9rem 1rem;
    margin-bottom:.8rem;
}}
.player-name {{ font-size:1rem; font-weight:700; color:{COLORS['text']}; }}
.player-meta {{ font-size:.78rem; color:{COLORS['muted']}; margin-top:.2rem; }}

</style>
"""


def apply() -> None:
    """Inject the global CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)
