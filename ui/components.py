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
    import numpy as np
    fig = go.Figure()

    shapes = [
        # Outer boundary
        dict(type="rect", x0=0, y0=0, x1=105, y1=68,
             line=dict(color="#3a5a3a", width=2.5), fillcolor="#1a3a1a"),
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
    theta = np.linspace(0, 2 * np.pi, 100)
    fig.add_trace(go.Scatter(
        x=52.5 + 9.15 * np.cos(theta),
        y=34   + 9.15 * np.sin(theta),
        mode="lines", line=dict(color="#3a5a3a", width=1.5),
        showlegend=False, hoverinfo="skip",
    ))

    # Corner arcs (1-yard radius)
    for cx, cy in [(0, 0), (105, 0), (0, 68), (105, 68)]:
        arc_angle = np.linspace(0, np.pi/2, 30)
        if cx == 0 and cy == 0:  # Bottom-left
            arc_x = 1 * np.cos(arc_angle + np.pi)
            arc_y = 1 * np.sin(arc_angle + np.pi)
        elif cx == 105 and cy == 0:  # Bottom-right
            arc_x = 105 - 1 * np.cos(arc_angle)
            arc_y = 1 * np.sin(arc_angle)
        elif cx == 0 and cy == 68:  # Top-left
            arc_x = 1 * np.cos(arc_angle)
            arc_y = 68 - 1 * np.sin(arc_angle)
        else:  # Top-right
            arc_x = 105 - 1 * np.cos(arc_angle + np.pi)
            arc_y = 68 - 1 * np.sin(arc_angle + np.pi)
        fig.add_trace(go.Scatter(
            x=arc_x, y=arc_y, mode="lines",
            line=dict(color="#3a5a3a", width=1), showlegend=False, hoverinfo="skip",
        ))

    # Penalty spots
    fig.add_trace(go.Scatter(
        x=[11, 94], y=[34, 34], mode="markers",
        marker=dict(size=3, color="#3a5a3a"), showlegend=False, hoverinfo="skip",
    ))

    # Center spot
    fig.add_trace(go.Scatter(
        x=[52.5], y=[34], mode="markers",
        marker=dict(size=3, color="#3a5a3a"), showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor="#1a3a1a",
        font=dict(color=COLORS["text"], size=12),
        height=500,
        margin=dict(t=20, b=20, l=20, r=20),
        legend=dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(
            range=[-2, 107],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            constrain="domain",
        ),
        yaxis=dict(
            range=[-2, 70],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
        ),
        hovermode="closest",
    )
    return fig


# ── 3D KPI Dashboard ──────────────────────────────────────────────────────────

def create_3d_kpi_dashboard(
    df,
    x_col: str, y_col: str, z_col: str,
    color_col: str = None,
    size_col: str = None,
    hover_cols: list = None,
    title: str = "3D KPI Dashboard"
) -> go.Figure:
    """Create a 3D scatter plot for multi-metric KPI visualization."""
    import pandas as pd
    import numpy as np

    hover_cols = hover_cols or []
    fig = go.Figure()

    def _format_val(v):
        try:
            if pd.isna(v):
                return "N/A"
            return f"{float(v):.2f}"
        except (TypeError, ValueError):
            return str(v)

    if color_col and color_col in df.columns:
        for color_val in df[color_col].unique():
            subset = df[df[color_col] == color_val]
            size_vals = subset[size_col] if size_col and size_col in subset.columns else 5

            hover_text = []
            for idx, (_, row) in enumerate(subset.iterrows()):
                player_name = row.get('player_name', f'Player {idx}')
                text = f"<b>{player_name}</b><br>"
                text += f"{x_col}: {_format_val(row[x_col])}<br>"
                text += f"{y_col}: {_format_val(row[y_col])}<br>"
                text += f"{z_col}: {_format_val(row[z_col])}<br>"
                for col in hover_cols:
                    if col in row.index:
                        text += f"{col}: {_format_val(row[col])}<br>"
                hover_text.append(text)

            fig.add_trace(go.Scatter3d(
                x=subset[x_col], y=subset[y_col], z=subset[z_col],
                mode="markers",
                name=str(color_val),
                marker=dict(
                    size=5 if not isinstance(size_vals, (list, np.ndarray)) else size_vals,
                    opacity=0.8,
                    line=dict(width=0.5, color=COLORS["bg"]),
                ),
                text=hover_text,
                hovertemplate="%{text}<extra></extra>",
            ))
    else:
        size_vals = df[size_col] if size_col and size_col in df.columns else 5
        hover_text = []
        for idx, (_, row) in enumerate(df.iterrows()):
            player_name = row.get('player_name', f'Player {idx}')
            text = f"<b>{player_name}</b><br>"
            text += f"{x_col}: {_format_val(row[x_col])}<br>"
            text += f"{y_col}: {_format_val(row[y_col])}<br>"
            text += f"{z_col}: {_format_val(row[z_col])}<br>"
            for col in hover_cols:
                if col in row.index:
                    text += f"{col}: {_format_val(row[col])}<br>"
            hover_text.append(text)

        fig.add_trace(go.Scatter3d(
            x=df[x_col], y=df[y_col], z=df[z_col],
            mode="markers",
            marker=dict(
                size=5 if not isinstance(size_vals, (list, np.ndarray)) else size_vals,
                color=COLORS["primary"],
                opacity=0.8,
                line=dict(width=0.5, color=COLORS["bg"]),
            ),
            text=hover_text,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(title=x_col, gridcolor="#2a4a2a"),
            yaxis=dict(title=y_col, gridcolor="#2a4a2a"),
            zaxis=dict(title=z_col, gridcolor="#2a4a2a"),
            bgcolor=COLORS["bg"],
        ),
        paper_bgcolor=COLORS["bg"],
        font=dict(color=COLORS["text"], size=11),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        legend=dict(bgcolor="rgba(0,0,0,0.5)"),
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
