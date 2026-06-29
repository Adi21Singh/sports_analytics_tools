"""Central configuration - colors, chart defaults."""

from __future__ import annotations

# ── Competition ───────────────────────────────────────────────────────────────
TEAM_NAME   = "La Liga"
SEASON      = "2015/16"
PITCH_LEN   = 105.0  # metres (display pitch, not StatsBomb coordinates)
PITCH_WID   = 68.0

# ── Design tokens ────────────────────────────────────────────────────────────
COLORS = {
    # backgrounds
    "bg":           "#0e1117",
    "surface":      "#1c1f26",
    "surface_alt":  "#23272f",
    "border":       "#2d3240",
    # accents
    "primary":      "#00c7a8",   # teal
    "secondary":    "#7c83fd",   # indigo
    "warning":      "#f59e0b",   # amber
    "danger":       "#ef4444",   # red
    "success":      "#22c55e",   # green
    # text
    "text":         "#f1f3f9",
    "muted":        "#9ca3af",
    # chart
    "grid":         "#2d3240",
}

PALETTE = ["#00c7a8", "#7c83fd", "#f59e0b", "#ef4444", "#22c55e",
           "#f472b6", "#38bdf8", "#fb923c", "#a3e635", "#e879f9"]

# ── Chart defaults (passed to update_layout) ─────────────────────────────────
CHART_BASE = dict(
    paper_bgcolor = COLORS["bg"],
    plot_bgcolor  = COLORS["surface"],
    font          = dict(color=COLORS["text"], size=12),
    margin        = dict(t=50, b=30, l=30, r=30),
    legend        = dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
    xaxis         = dict(gridcolor=COLORS["grid"], zeroline=False),
    yaxis         = dict(gridcolor=COLORS["grid"], zeroline=False),
)
