"""Reusable UI building blocks — all return HTML strings or call st directly."""

from __future__ import annotations
import plotly.graph_objects as go
import streamlit as st
from config import COLORS, CHART_BASE, ACWR_ZONES


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

def section_header(title: str, subtitle: str = "", icon: str = "") -> None:
    icon_span = f'<span style="font-size:1.2rem;">{icon}</span>' if icon else ""
    sub_html  = f'<p class="section-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="section-header">{icon_span}<h3>{title}</h3></div>{sub_html}',
        unsafe_allow_html=True,
    )


# ── Risk badge ────────────────────────────────────────────────────────────────

_BADGE_CLASS = {
    "Optimal":        "badge-optimal",
    "Caution":        "badge-caution",
    "High Risk":      "badge-high",
    "Under-training": "badge-under",
}

def risk_badge(zone: str) -> str:
    cls = _BADGE_CLASS.get(zone, "badge-under")
    return f'<span class="badge {cls}">{zone}</span>'


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
    fig = go.Figure()

    shapes = [
        # Outer boundary
        dict(type="rect", x0=0, y0=0, x1=105, y1=68,
             line=dict(color="#3a5a3a", width=2), fillcolor="#1a3a1a"),
        # Left penalty area
        dict(type="rect", x0=0,    y0=13.84, x1=16.5, y1=54.16,
             line=dict(color="#3a5a3a", width=1.5), fillcolor="rgba(0,0,0,0)"),
        # Right penalty area
        dict(type="rect", x0=88.5, y0=13.84, x1=105,  y1=54.16,
             line=dict(color="#3a5a3a", width=1.5), fillcolor="rgba(0,0,0,0)"),
        # Left 6-yard box
        dict(type="rect", x0=0,    y0=24.84, x1=5.5,  y1=43.16,
             line=dict(color="#3a5a3a", width=1.2), fillcolor="rgba(0,0,0,0)"),
        # Right 6-yard box
        dict(type="rect", x0=99.5, y0=24.84, x1=105,  y1=43.16,
             line=dict(color="#3a5a3a", width=1.2), fillcolor="rgba(0,0,0,0)"),
        # Halfway line
        dict(type="line", x0=52.5, y0=0, x1=52.5, y1=68,
             line=dict(color="#3a5a3a", width=1.5)),
        # Right goal
        dict(type="rect", x0=105,  y0=30.34, x1=106.5, y1=37.66,
             line=dict(color="#8892b0", width=2), fillcolor=COLORS["bg"]),
        # Left goal
        dict(type="rect", x0=-1.5, y0=30.34, x1=0, y1=37.66,
             line=dict(color="#8892b0", width=2), fillcolor=COLORS["bg"]),
    ]
    for s in shapes:
        fig.add_shape(**s)

    # Centre circle
    import numpy as np
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=52.5 + 9.15 * np.cos(theta),
        y=34   + 9.15 * np.sin(theta),
        mode="lines", line=dict(color="#3a5a3a", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor="#1a3a1a",
        font=dict(color=COLORS["text"], size=12),
        height=480,
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(range=[-4, 112], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-4, 72],  showgrid=False, zeroline=False, showticklabels=False,
                   scaleanchor="x", scaleratio=1),
    )
    return fig


# ── Empty state ───────────────────────────────────────────────────────────────

def empty_state(message: str = "No data available for the selected filters.") -> None:
    st.markdown(
        f'<div style="text-align:center;padding:3rem;color:{COLORS["muted"]};'
        f'background:{COLORS["surface"]};border-radius:12px;border:1px dashed {COLORS["border"]};">'
        f'<div style="font-size:2rem;margin-bottom:.5rem;">📭</div>'
        f'<div>{message}</div></div>',
        unsafe_allow_html=True,
    )
