"""Reusable UI building blocks - all return HTML strings or call st directly."""

from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
from config import COLORS, CHART_BASE


# ── KPI card ──────────────────────────────────────────────────────────────────

def kpi_card(
    label: str,
    value: str,
    delta: float | None = None,
    delta_label: str = "",
    sub: str = "",
    accent: str = COLORS["primary"],
) -> str:
    """Return an HTML KPI card. Render with st.markdown(..., unsafe_allow_html=True)."""
    delta_html = ""
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        cls  = "pos" if delta >= 0 else "neg"
        delta_html = f'<div class="kpi-delta delta-{cls}">{sign}{delta:.1f} {delta_label}</div>'

    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""

    return (
        f'<div class="kpi-card" style="--accent:{accent};">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  {delta_html}{sub_html}'
        f'</div>'
    )


def kpi_row(cards: list[str]) -> None:
    """Render a list of kpi_card() strings evenly across columns."""
    cols = st.columns(len(cards))
    for col, html in zip(cols, cards):
        col.markdown(html, unsafe_allow_html=True)


# ── Section header ────────────────────────────────────────────────────────────

def section_header(title: str, subtitle: str = "", icon: str = "", help_text: str = "") -> None:
    icon_span = f'<span style="font-size:1.2rem;">{icon}</span>' if icon else ""
    sub_html  = f'<p class="section-sub">{subtitle}</p>' if subtitle else ""
    html = f'<div class="section-header">{icon_span}<h3>{title}</h3></div>{sub_html}'
    if help_text:
        c1, c2 = st.columns([18, 1])
        with c1:
            st.markdown(html, unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
            with st.popover("ⓘ", width="stretch"):
                st.markdown(help_text, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(html, unsafe_allow_html=True)


def info_popover(text: str) -> None:
    """Standalone ⓘ popover for inline use next to any element."""
    with st.popover("ⓘ", width="content"):
        st.markdown(text, unsafe_allow_html=True)


# ── Match hero ────────────────────────────────────────────────────────────────

def match_hero(
    home: str,
    away: str,
    analysing: str,
    date: str = "",
    competition: str = "",
    match_week: str = "",
) -> None:
    """Render the full-width match header with team names and context."""
    home_role  = "analysing ▲" if analysing == home else "home"
    away_role  = "analysing ▲" if analysing == away else "away"
    home_cls   = "active" if analysing == home else ""
    away_cls   = "active" if analysing == away else ""

    meta_parts = [p for p in [competition, date, match_week] if p]
    meta_html  = " &nbsp;·&nbsp; ".join(meta_parts) if meta_parts else ""

    st.markdown(f"""
<div class="match-hero">
  <div class="hero-team">
    <div class="hero-team-name">{home}</div>
    <div class="hero-team-role {home_cls}">{home_role}</div>
  </div>
  <div class="hero-center">
    <div class="hero-vs">VS</div>
    <div class="hero-meta">{meta_html}</div>
    <div class="hero-badge">La Liga · StatsBomb</div>
  </div>
  <div class="hero-team away">
    <div class="hero-team-name">{away}</div>
    <div class="hero-team-role {away_cls}">{away_role}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Press verdict card ────────────────────────────────────────────────────────

def verdict_card(
    title: str,
    description: str,
    icon: str,
    stat_value: str,
    stat_label: str,
    level: str = "good",   # "good" | "warn" | "bad" | "neutral"
) -> None:
    """Render the bold press verdict summary card."""
    palette = {
        "good":    (COLORS["success"],  "#0d2e1a", "#1a5c30"),
        "warn":    (COLORS["warning"],  "#2e1f00", "#5c3d00"),
        "bad":     (COLORS["danger"],   "#2e0d0d", "#5c1a1a"),
        "neutral": (COLORS["muted"],    COLORS["surface"], COLORS["border"]),
    }
    color, bg, border = palette.get(level, palette["neutral"])
    label_text = title.upper().replace(" ", "_")

    st.markdown(f"""
<div class="verdict-card" style="--v-color:{color};--v-bg:{bg};--v-border:{border};--v-label:'{label_text}';">
  <div class="verdict-icon">{icon}</div>
  <div class="verdict-body">
    <div class="verdict-title">{title}</div>
    <div class="verdict-desc">{description}</div>
  </div>
  <div>
    <div class="verdict-stat">{stat_value}</div>
    <div class="verdict-stat-label">{stat_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Stat strip ────────────────────────────────────────────────────────────────

def stat_strip(items: list[dict]) -> None:
    """
    Render a horizontal strip of stats.
    Each item: {"label": str, "value": str, "color": str (optional)}
    """
    cells = ""
    for item in items:
        color = item.get("color", COLORS["primary"])
        cells += f"""
<div class="stat-strip-item" style="--s-color:{color};">
  <div class="stat-strip-val">{item['value']}</div>
  <div class="stat-strip-label">{item['label']}</div>
</div>"""
    st.markdown(f'<div class="stat-strip">{cells}</div>', unsafe_allow_html=True)


# ── Info box ──────────────────────────────────────────────────────────────────

def info_box(text: str) -> None:
    st.markdown(f'<div class="info-box">{text}</div>', unsafe_allow_html=True)


# ── Chart styling helper ──────────────────────────────────────────────────────

def style_chart(fig: go.Figure, height: int = 320, **overrides) -> go.Figure:
    """Apply CHART_BASE defaults + optional overrides to a figure."""
    layout = {**CHART_BASE, "height": height, **overrides}
    fig.update_layout(**layout)
    return fig


# ── Pitch drawing ─────────────────────────────────────────────────────────────

def draw_pitch() -> go.Figure:
    """Return a blank Plotly figure with a football pitch drawn on it."""
    import numpy as np

    _LINE  = "#ffffff"          # white markings - clearly visible on green
    _PITCH = "#1a6b2f"          # football pitch green
    _GOAL  = "rgba(0,0,0,0.45)" # slightly darkened goal boxes
    _W     = 1.8                # standard line width
    _WH    = 2.5                # heavier outer boundary

    fig = go.Figure()

    # ── Pitch shapes ─────────────────────────────────────────────────────────
    shapes = [
        dict(type="rect", x0=0,    y0=0,     x1=105,  y1=68,    # outer boundary
             line=dict(color=_LINE, width=_WH), fillcolor=_PITCH,           layer="below"),
        dict(type="rect", x0=0,    y0=13.84, x1=16.5, y1=54.16, # left penalty area
             line=dict(color=_LINE, width=_W),  fillcolor="rgba(0,0,0,0)",  layer="below"),
        dict(type="rect", x0=88.5, y0=13.84, x1=105,  y1=54.16, # right penalty area
             line=dict(color=_LINE, width=_W),  fillcolor="rgba(0,0,0,0)",  layer="below"),
        dict(type="rect", x0=0,    y0=24.84, x1=5.5,  y1=43.16, # left 6-yard box
             line=dict(color=_LINE, width=_W),  fillcolor="rgba(0,0,0,0)",  layer="below"),
        dict(type="rect", x0=99.5, y0=24.84, x1=105,  y1=43.16, # right 6-yard box
             line=dict(color=_LINE, width=_W),  fillcolor="rgba(0,0,0,0)",  layer="below"),
        dict(type="line", x0=52.5, y0=0,     x1=52.5, y1=68,    # halfway line
             line=dict(color=_LINE, width=_W),                               layer="below"),
        dict(type="rect", x0=105,  y0=30.34, x1=107,  y1=37.66, # right goal
             line=dict(color=_LINE, width=_W),  fillcolor=_GOAL,            layer="below"),
        dict(type="rect", x0=-2,   y0=30.34, x1=0,    y1=37.66, # left goal
             line=dict(color=_LINE, width=_W),  fillcolor=_GOAL,            layer="below"),
    ]
    for s in shapes:
        fig.add_shape(**s)

    _lkw = dict(mode="lines", showlegend=False, hoverinfo="skip")
    _mkw = dict(mode="markers", showlegend=False, hoverinfo="skip")

    # ── Centre circle ─────────────────────────────────────────────────────────
    theta = np.linspace(0, 2 * np.pi, 120)
    fig.add_trace(go.Scatter(
        x=52.5 + 9.15 * np.cos(theta),
        y=34   + 9.15 * np.sin(theta),
        line=dict(color=_LINE, width=_W), **_lkw,
    ))

    # ── Penalty arcs (the D) ──────────────────────────────────────────────────
    arc_half = float(np.arccos(5.5 / 9.15))   # ≈ 0.928 rad - where arc exits box

    # Left D (arc faces right, outside the left penalty box)
    t_L = np.linspace(-arc_half, arc_half, 60)
    fig.add_trace(go.Scatter(
        x=11  + 9.15 * np.cos(t_L), y=34 + 9.15 * np.sin(t_L),
        line=dict(color=_LINE, width=_W), **_lkw,
    ))

    # Right D (arc faces left, outside the right penalty box)
    t_R = np.linspace(np.pi - arc_half, np.pi + arc_half, 60)
    fig.add_trace(go.Scatter(
        x=94  + 9.15 * np.cos(t_R), y=34 + 9.15 * np.sin(t_R),
        line=dict(color=_LINE, width=_W), **_lkw,
    ))

    # ── Corner arcs (1 m radius, curving into the pitch) ─────────────────────
    for cx, cy, t_start, t_end in [
        (  0,  0,  0,          np.pi / 2),       # bottom-left
        (105,  0,  np.pi / 2,  np.pi),            # bottom-right
        (  0, 68, -np.pi / 2,  0),                # top-left
        (105, 68,  np.pi,      3 * np.pi / 2),    # top-right
    ]:
        t = np.linspace(t_start, t_end, 30)
        fig.add_trace(go.Scatter(
            x=cx + np.cos(t), y=cy + np.sin(t),
            line=dict(color=_LINE, width=1.2), **_lkw,
        ))

    # ── Spots (penalty + centre) ──────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=[11, 94, 52.5], y=[34, 34, 34],
        marker=dict(size=5, color=_LINE), **_mkw,
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=_PITCH,
        font=dict(color=COLORS["text"], size=12),
        height=480,
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(range=[-3, 108], showgrid=False, zeroline=False,
                   showticklabels=False),
        yaxis=dict(range=[-2, 70],  showgrid=False, zeroline=False,
                   showticklabels=False),
        hovermode="closest",
    )
    return fig

