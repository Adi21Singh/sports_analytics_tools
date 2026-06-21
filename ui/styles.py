"""Single source of truth for all injected CSS."""

import streamlit as st
from config import COLORS


_CSS = f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');

/* ── Layout ──────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"]  {{ background:{COLORS['bg']}; }}
[data-testid="stSidebar"]           {{ background:{COLORS['surface']}; border-right:1px solid {COLORS['border']}; }}
section.main > div                  {{ padding-top:1.2rem; }}

/* ── Typography ──────────────────────────────────────────────── */
h1,h2,h3,h4 {{ color:{COLORS['text']}; font-weight:700; font-family:'Inter',sans-serif; }}
p, li        {{ color:{COLORS['muted']}; line-height:1.6; font-family:'Inter',sans-serif; }}
label        {{ color:{COLORS['muted']} !important; font-size:0.8rem; }}

/* ── Tabs ────────────────────────────────────────────────────── */
[data-testid="stTabs"] button {{
    color: {COLORS['muted']};
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 6px 6px 0 0;
    font-family: 'Inter', sans-serif;
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
    border-radius: 12px;
    padding: 1.4rem 1.4rem 1.2rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, {COLORS['primary']});
    border-radius: 12px 12px 0 0;
}}
.kpi-label   {{ font-size:0.68rem; color:{COLORS['muted']}; text-transform:uppercase; letter-spacing:.09em; margin-bottom:.5rem; font-family:'Inter',sans-serif; }}
.kpi-value   {{ font-size:2.4rem; font-weight:400; color:{COLORS['text']}; line-height:1; font-family:'Bebas Neue',sans-serif; letter-spacing:.02em; }}
.kpi-delta   {{ font-size:0.78rem; margin-top:.3rem; }}
.delta-pos   {{ color:{COLORS['success']}; }}
.delta-neg   {{ color:{COLORS['danger']};  }}
.delta-neu   {{ color:{COLORS['muted']};   }}
.kpi-sub     {{ font-size:0.72rem; color:{COLORS['muted']}; margin-top:.3rem; font-family:'DM Mono',monospace; }}

/* ── Match hero ──────────────────────────────────────────────── */
.match-hero {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin: 0 0 1.8rem;
    position: relative;
    overflow: hidden;
}}
.match-hero::before {{
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, {COLORS['primary']}08 0%, transparent 60%);
    pointer-events: none;
}}
.hero-team {{
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: .3rem;
}}
.hero-team.away {{ text-align: right; align-items: flex-end; }}
.hero-team-name {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: {COLORS['text']};
    letter-spacing: .05em;
    line-height: 1;
}}
.hero-team-role {{
    font-size: .68rem;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: {COLORS['muted']};
    font-family: 'DM Mono', monospace;
}}
.hero-team-role.active {{
    color: {COLORS['primary']};
    font-weight: 500;
}}
.hero-center {{
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .4rem;
    padding: 0 2.5rem;
}}
.hero-vs {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.2rem;
    color: {COLORS['border']};
    letter-spacing: .15em;
}}
.hero-meta {{
    font-size: .7rem;
    color: {COLORS['muted']};
    font-family: 'DM Mono', monospace;
    text-align: center;
    line-height: 1.6;
}}
.hero-badge {{
    background: {COLORS['primary']}18;
    border: 1px solid {COLORS['primary']}40;
    border-radius: 20px;
    padding: .25rem .9rem;
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: {COLORS['primary']};
    font-family: 'Inter', sans-serif;
    font-weight: 600;
}}

/* ── Press verdict card ──────────────────────────────────────── */
.verdict-card {{
    border-radius: 14px;
    padding: 1.8rem 2rem;
    margin: 1rem 0 1.6rem;
    display: flex;
    align-items: center;
    gap: 2rem;
    position: relative;
    overflow: hidden;
    border: 1px solid var(--v-border);
    background: var(--v-bg);
}}
.verdict-card::after {{
    content: var(--v-label);
    position: absolute;
    right: 2rem;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 5rem;
    color: var(--v-border);
    opacity: .18;
    letter-spacing: .05em;
    pointer-events: none;
    line-height: 1;
}}
.verdict-icon {{
    font-size: 2.4rem;
    line-height: 1;
    flex-shrink: 0;
}}
.verdict-body {{ flex: 1; }}
.verdict-title {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: .06em;
    color: var(--v-color);
    line-height: 1;
    margin-bottom: .3rem;
}}
.verdict-desc {{
    font-size: .84rem;
    color: {COLORS['muted']};
    line-height: 1.5;
    font-family: 'Inter', sans-serif;
    max-width: 560px;
}}
.verdict-stat {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem;
    color: var(--v-color);
    line-height: 1;
    flex-shrink: 0;
    text-align: center;
}}
.verdict-stat-label {{
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .1em;
    color: {COLORS['muted']};
    font-family: 'DM Mono', monospace;
    text-align: center;
    margin-top: .2rem;
}}

/* ── Section header ──────────────────────────────────────────── */
.section-header {{
    display:flex; align-items:center; gap:.6rem;
    margin: 1.6rem 0 .6rem;
    padding-bottom: .6rem;
    border-bottom: 1px solid {COLORS['border']};
}}
.section-header h3 {{
    margin:0; font-size:1rem;
    color:{COLORS['text']};
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    letter-spacing: .01em;
}}
.section-sub {{ font-size:.78rem; color:{COLORS['muted']}; margin:.15rem 0 0; font-family:'DM Mono',monospace; }}

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
    font-size:.82rem;
    color:{COLORS['muted']};
    font-family: 'Inter', sans-serif;
}}

/* ── Sidebar player card ──────────────────────────────────────── */
.player-card {{
    background:{COLORS['surface_alt']};
    border:1px solid {COLORS['border']};
    border-radius:12px;
    padding:.9rem 1rem;
    margin-bottom:.8rem;
}}
.player-name {{ font-size:1rem; font-weight:700; color:{COLORS['text']}; font-family:'Inter',sans-serif; }}
.player-meta {{ font-size:.78rem; color:{COLORS['muted']}; margin-top:.2rem; font-family:'DM Mono',monospace; }}

/* ── Stat strip ──────────────────────────────────────────────── */
.stat-strip {{
    display: flex;
    gap: 0;
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    overflow: hidden;
    margin: 1.2rem 0;
}}
.stat-strip-item {{
    flex: 1;
    padding: 1.1rem 1.4rem;
    background: {COLORS['surface']};
    border-right: 1px solid {COLORS['border']};
    position: relative;
}}
.stat-strip-item:last-child {{ border-right: none; }}
.stat-strip-item::before {{
    content: "";
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: var(--s-color, {COLORS['primary']});
    opacity: .7;
}}
.stat-strip-val {{
    font-family: 'Bebas Neue', sans-serif;
    font-size: 2rem;
    color: var(--s-color, {COLORS['text']});
    line-height: 1;
}}
.stat-strip-label {{
    font-size: .65rem;
    text-transform: uppercase;
    letter-spacing: .09em;
    color: {COLORS['muted']};
    font-family: 'DM Mono', monospace;
    margin-top: .3rem;
}}

</style>
"""


def apply() -> None:
    """Inject the global CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)
