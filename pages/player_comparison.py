"""Player Comparison — radar overlay, head-to-head stats, season trends."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, section_header, style_chart, info_box, empty_state
from ui.data_source import render_data_source_selector, get_data
from analytics.performance import (
    build_radar_profile, compute_derived_kpis,
    z_score_table, percentile_rank, RADAR_METRICS,
)
from config import COLORS, PALETTE

styles.apply()

# ── Sidebar phase 1 — data source ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔄 Player Comparison")
    render_data_source_selector()

players, training, wellness, matches, match_players, events = get_data()
match_players = compute_derived_kpis(match_players)

# ── Sidebar phase 2 — player selector ────────────────────────────────────────
with st.sidebar:
    all_names = sorted(players["name"].tolist())
    selected  = st.multiselect("Select Players (2–4)", all_names,
                               default=all_names[:2], max_selections=4)

if len(selected) < 2:
    st.warning("Select at least 2 players from the sidebar.")
    st.stop()

pids = [int(players[players["name"] == n]["id"].values[0]) for n in selected]

st.title("🔄 Player Comparison")
st.caption(" · ".join(f"**{n}**" for n in selected))
st.divider()

tab1, tab2, tab3 = st.tabs(["🕸 Radar Overlay", "📊 Head-to-Head", "📈 Season Trends"])

COMP_COLORS = PALETTE[:4]

# ═══════════════════════════════════════════════════════════════════════════════
# RADAR OVERLAY
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("Performance Profile — Percentile vs Squad", icon="🕸")
    info_box("Each axis shows each player's percentile rank within the full squad (0 = lowest · 100 = highest).")

    labels = list(RADAR_METRICS.values())
    fig = go.Figure()
    for pid, pname, color in zip(pids, selected, COMP_COLORS):
        radar = build_radar_profile(pid, match_players)
        if not radar: continue
        vals = [radar[k]["percentile"] for k in RADAR_METRICS]
        vals_c = vals + [vals[0]]
        labs_c = labels + [labels[0]]
        # Parse hex to rgba
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=labs_c, fill="toself", name=pname,
            fillcolor=f"rgba({r},{g},{b},0.12)",
            line=dict(color=color, width=2.5),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor=COLORS["surface"],
            radialaxis=dict(visible=True, range=[0, 100],
                            gridcolor=COLORS["border"],
                            tickfont=dict(color=COLORS["muted"])),
            angularaxis=dict(gridcolor=COLORS["border"],
                             tickfont=dict(color=COLORS["text"])),
        ),
        paper_bgcolor=COLORS["bg"], height=520,
        legend=dict(x=0.82, y=0.98, bgcolor=COLORS["surface"],
                    bordercolor=COLORS["border"], borderwidth=1),
        margin=dict(t=60, b=40),
    )
    st.plotly_chart(fig, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# HEAD-TO-HEAD
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("Head-to-Head Statistical Comparison", icon="📊")

    all_metrics = [
        "goals", "assists", "xg", "xa", "shots", "passes",
        "pass_completion", "progressive_passes", "key_passes", "dribbles_won",
        "tackles_won", "pressures", "aerial_duels_won", "touches_in_box",
        "distance_m", "hsr_m", "sprint_count", "max_speed_kmh", "match_rating",
    ]

    rows = {}
    for pid, pname in zip(pids, selected):
        pm = match_players[match_players["player_id"] == pid]
        if pm.empty: continue
        agg = {}
        for m in all_metrics:
            if m in ["goals", "assists"]:
                agg[m] = round(float(pm[m].sum()), 1)
            else:
                agg[m] = round(float(pm[m].mean()), 2)
        rows[pname] = agg

    if rows:
        display_df = pd.DataFrame(rows).T.astype(float)
        display_df.index.name = "Player"
        rename = {m: m.replace("_m","").replace("_"," ").title() for m in all_metrics}
        display_df.columns = [rename.get(c, c) for c in display_df.columns]
        st.dataframe(display_df, width="stretch")

        # Grouped bar chart — key metrics
        key_m = {
            "Goals (total)":   "goals",      "Assists (total)": "assists",
            "xG (total)":      "xg",         "Shots/match":     "shots",
            "Key Passes/match":"key_passes",  "Dribbles Won":    "dribbles_won",
            "Tackles Won":     "tackles_won", "Match Rating":    "match_rating",
        }
        long = []
        for pid, pname in zip(pids, selected):
            pm = match_players[match_players["player_id"] == pid]
            if pm.empty: continue
            for label, col in key_m.items():
                val = float(pm[col].sum()) if col in ["goals","assists","xg"] else float(pm[col].mean())
                long.append({"Player": pname, "Metric": label, "Value": round(val, 2)})

        long_df = pd.DataFrame(long)
        long_df["Value"] = pd.to_numeric(long_df["Value"], errors="coerce").astype(float)
        fig = px.bar(long_df, x="Metric", y="Value", color="Player",
                     barmode="group", color_discrete_sequence=COMP_COLORS,
                     labels={"Value": "Value", "Metric": ""})
        fig = style_chart(fig, height=380,
                          xaxis=dict(tickangle=-30, gridcolor=COLORS["grid"]),
                          yaxis=dict(title="Value", gridcolor=COLORS["grid"]))
        fig.update_layout(title="Key Metrics Comparison",
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# SEASON TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    section_header("Season Form Comparison", icon="📈")
    metric_choice = st.selectbox("Metric", [
        "match_rating", "xg", "xa", "goals", "shots", "passes",
        "key_passes", "dribbles_won", "tackles_won", "distance_m", "hsr_m",
    ], format_func=lambda x: x.replace("_m","").replace("_"," ").title())

    fig = go.Figure()
    for pid, pname, color in zip(pids, selected, COMP_COLORS):
        pm = match_players[match_players["player_id"] == pid].sort_values("date")
        if pm.empty: continue
        rolling = pm[metric_choice].rolling(4, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=pm["date"], y=rolling, mode="lines+markers",
            name=pname, line=dict(color=color, width=2.5), marker=dict(size=6),
        ))
    fig = style_chart(fig, height=360,
                      xaxis=dict(title="Date", gridcolor=COLORS["grid"]),
                      yaxis=dict(title=metric_choice.replace("_m","").replace("_"," ").title(),
                                 gridcolor=COLORS["grid"]))
    fig.update_layout(title="4-Match Rolling Average — Form Trend",
                      legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, width="stretch")

    # Percentile rank bars
    section_header("Percentile Rankings vs Full Squad", icon="📐")
    z_metrics_list = ["distance_m","hsr_m","shots","goals","assists",
                      "xg","key_passes","dribbles_won","tackles_won","match_rating"]
    z_df = z_score_table(match_players, z_metrics_list)

    pct_rows = []
    for pid, pname in zip(pids, selected):
        pr = z_df[z_df["player_id"] == pid]
        if pr.empty: continue
        for m in z_metrics_list:
            val = float(pr[m].values[0])
            pct = percentile_rank(val, z_df[m])
            pct_rows.append({"Player": pname,
                             "Metric": m.replace("_m","").replace("_"," ").title(),
                             "Percentile": pct})

    pct_df = pd.DataFrame(pct_rows)
    if not pct_df.empty:
        fig2 = px.bar(pct_df, x="Percentile", y="Metric", color="Player",
                      barmode="group", color_discrete_sequence=COMP_COLORS,
                      labels={"Percentile": "Squad Percentile (%)", "Metric": ""})
        fig2.add_vline(x=50, line_dash="dash", line_color=COLORS["muted"],
                       annotation_text="Squad Median")
        fig2 = style_chart(fig2, height=380,
                           xaxis=dict(range=[0, 105], title="Percentile (%)", gridcolor=COLORS["grid"]),
                           yaxis=dict(gridcolor=COLORS["grid"]))
        fig2.update_layout(title="Squad Percentile Comparison",
                           margin=dict(l=120), legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig2, width="stretch")
