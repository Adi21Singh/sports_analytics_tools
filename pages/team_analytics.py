"""Team Analytics - clustering, PCA, Z-scores, top performers, season trends."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, info_box, info_popover
from ui.data_source import render_data_source_selector, get_data
from analytics.performance import compute_derived_kpis, z_score_table, percentile_rank
from analytics.clustering import cluster_players, CLUSTER_FEATURES
from config import COLORS, PALETTE

styles.apply()

# ── Sidebar (all controls are data-independent here) ─────────────────────────
with st.sidebar:
    st.markdown("### 🏆 Team Analytics")
    render_data_source_selector()
    n_clusters = st.slider("K-means Clusters", 3, 7, 5)
    z_metrics = st.multiselect(
        "Metrics for Z-score Table",
        ["distance_m", "hsr_m", "sprint_count", "passes", "shots",
         "goals", "assists", "xg", "xa", "key_passes",
         "tackles_won", "pressures", "dribbles_won", "match_rating"],
        default=["distance_m", "xg", "goals", "assists", "tackles_won", "match_rating"],
    )

players, training, wellness, matches, match_players, events = get_data()
match_players = compute_derived_kpis(match_players)

st.title("🏆 Team Analytics")
st.divider()

# ── Season KPIs ───────────────────────────────────────────────────────────────
wins  = int((matches["result"] == "Win").sum())
draws = int((matches["result"] == "Draw").sum())
losses= int((matches["result"] == "Loss").sum())
gf    = int(matches["goals_for"].sum())
ga    = int(matches["goals_against"].sum())

section_header("Season Snapshot", icon="📋",
               help_text=(
                   "High-level team performance metrics for the current season.<br><br>"
                   "<b>Win Rate</b> - % of matches won.<br>"
                   "<b>Goal Difference</b> - total goals scored minus conceded. A positive GD is a reliable indicator of league position.<br>"
                   "<b>Avg Possession</b> - mean ball possession % across all matches.<br>"
                   "<b>Avg PPDA</b> - Passes Allowed Per Defensive Action. "
                   "Below 10 = high pressing team. Above 10 = more passive/mid-block approach."
               ))
kpi_row([
    kpi_card("Win Rate",        f"{wins/len(matches)*100:.0f}%",       accent=COLORS["success"]),
    kpi_card("Goals Scored",    gf,                                     accent=COLORS["primary"]),
    kpi_card("Goals Conceded",  ga,                                     accent=COLORS["danger"]),
    kpi_card("Goal Difference", f"{gf - ga:+d}",                       accent=COLORS["secondary"]),
    kpi_card("Avg Possession",  f"{matches['possession_pct'].mean():.1f}%", accent=COLORS["warning"]),
    kpi_card("Avg PPDA",        f"{matches['ppda'].mean():.1f}",        accent=COLORS["primary"]),
])
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 Season Trends", "🔬 Player Clustering", "📊 Z-Score Benchmarks", "🏅 Top Performers"])

# ═══════════════════════════════════════════════════════════════════════════════
# SEASON TRENDS
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    df_m = matches.sort_values("date").copy()
    df_m["match_no"] = range(1, len(df_m) + 1)
    df_m["cum_pts"]  = df_m["result"].map({"Win": 3, "Draw": 1, "Loss": 0}).cumsum()
    df_m["cum_gf"]   = df_m["goals_for"].cumsum()
    df_m["cum_ga"]   = df_m["goals_against"].cumsum()

    section_header("Cumulative Season Performance", icon="📈",
                   help_text=(
                       "Tracks how cumulative points, goals scored and goals conceded have accumulated match by match.<br><br>"
                       "A steep points curve = good run of form. A flattening curve = poor results. "
                       "When the goals conceded line rises sharply while goals scored stays flat, "
                       "the team is defending poorly but not converting either - a structural problem."
                   ))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_m["match_no"], y=df_m["cum_pts"],
                             mode="lines+markers", name="Points",
                             line=dict(color=COLORS["primary"], width=2.5)))
    fig.add_trace(go.Scatter(x=df_m["match_no"], y=df_m["cum_gf"],
                             mode="lines+markers", name="Goals For",
                             line=dict(color=COLORS["success"], width=2)))
    fig.add_trace(go.Scatter(x=df_m["match_no"], y=df_m["cum_ga"],
                             mode="lines+markers", name="Goals Against",
                             line=dict(color=COLORS["danger"], width=2, dash="dot")))
    fig = style_chart(fig, height=300,
                      xaxis=dict(title="Match", gridcolor=COLORS["grid"]),
                      yaxis=dict(title="Cumulative", gridcolor=COLORS["grid"]))
    st.plotly_chart(fig, width="stretch")

    l, r = st.columns(2)
    with l:
        color_map = {"Win": COLORS["success"], "Draw": COLORS["warning"], "Loss": COLORS["danger"]}
        fig2 = px.scatter(df_m, x="possession_pct", y="goals_for",
                          color="result", color_discrete_map=color_map,
                          hover_data=["opponent"],
                          labels={"possession_pct": "Possession %", "goals_for": "Goals"},
                          title="Possession vs Goals Scored")
        fig2 = style_chart(fig2, height=280)
        st.plotly_chart(fig2, width="stretch")
    with r:
        ha = df_m.groupby(["home_away", "result"]).size().reset_index(name="n")
        fig3 = px.bar(ha, x="home_away", y="n", color="result",
                      color_discrete_map=color_map, barmode="group",
                      labels={"home_away": "Venue", "n": "Matches"},
                      title="Home vs Away Results")
        fig3 = style_chart(fig3, height=280)
        st.plotly_chart(fig3, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("K-Means Player Role Clustering", icon="🔬",
                   help_text=(
                       "Unsupervised machine learning groups players into clusters based on their statistical profiles - "
                       "without being told positions in advance.<br><br>"
                       "Players in the same cluster have similar playing patterns. "
                       "Clusters often map onto recognisable roles (high-press forwards, deep-lying playmakers, defensive midfielders etc.) "
                       "but discovered from the data, not assumed from squad sheets.<br><br>"
                       "<b>How to use it:</b> if two very different players land in the same cluster, they may be more interchangeable than assumed. "
                       "If a player is isolated in their own cluster, they have a unique profile in the squad - they may be hard to replace.<br><br>"
                       "Use the sidebar slider to change K (number of clusters). Higher K = finer role distinctions."
                   ))
    info_box(
        f"Players grouped into <b>{n_clusters}</b> archetypes using K-means on "
        "match-averaged performance features, projected to 2D via PCA. "
        "Bubble size = average match rating."
    )

    with st.spinner("Running K-means…"):
        cluster_df = cluster_players(match_players, n_clusters=n_clusters)

    ev = cluster_df["explained_var_pct"].iloc[0]
    st.caption(f"PCA explains **{ev:.1f}%** of total variance across {len(CLUSTER_FEATURES)} features.")

    fig = px.scatter(
        cluster_df, x="pca_x", y="pca_y",
        color="cluster_label", symbol="position",
        size="match_rating",
        hover_data=["player_name", "position"] + CLUSTER_FEATURES[:4],
        color_discrete_sequence=PALETTE,
        labels={"pca_x": "PCA Dimension 1", "pca_y": "PCA Dimension 2"},
        title="Player Role Map - PCA of Match Performance",
    )
    fig = style_chart(fig, height=480)
    fig.update_traces(marker=dict(sizemin=6, line=dict(width=0.5, color=COLORS["border"])))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Cluster Average Stats")
    summary = (cluster_df.groupby("cluster_label")[CLUSTER_FEATURES]
               .mean().round(1).reset_index())
    st.dataframe(summary, width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Z-SCORES
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    section_header("Squad Z-Score Benchmarking", icon="📊",
                   help_text=(
                       "Z-scores measure how many standard deviations a player is above or below the squad average for each metric.<br><br>"
                       "<b>Z = 0</b> = exactly squad average.<br>"
                       "<b>Z = +2</b> = exceptional (top ~2% of the squad).<br>"
                       "<b>Z = -2</b> = well below average for the group.<br><br>"
                       "This is useful for spotting outliers - either exceptional performers worth building around "
                       "or underperformers in specific metrics who may need coaching focus or positional adjustment.<br><br>"
                       "Select which metrics to include using the sidebar multiselect."
                   ))
    info_box(
        "<b>Z-score</b> = (player value − squad mean) / squad std. "
        "<b>+1.0</b> = one standard deviation above squad average. "
        "Green = above average · Red = below average."
    )

    if not z_metrics:
        st.info("Select metrics in the sidebar.")
    else:
        z_df = z_score_table(match_players, z_metrics)
        z_cols  = [m + "_z" for m in z_metrics]
        display = z_df[["player_name", "position"] + z_cols].copy()
        display.columns = (["Player", "Position"] +
                           [m.replace("_m", "").replace("_", " ").title() for m in z_metrics])

        def _colour_z(val):
            try:
                v = float(val)
                if v >=  1.5: return f"background-color:#0d3324;color:{COLORS['success']}"
                if v >=  0.5: return f"background-color:#162b1a;color:#a8d8a8"
                if v <= -1.5: return f"background-color:#3a0d0d;color:{COLORS['danger']}"
                if v <= -0.5: return f"background-color:#2e1010;color:#ff9f9f"
            except: pass
            return ""

        metric_display_cols = display.columns[2:]
        st.dataframe(
            display.style.map(_colour_z, subset=metric_display_cols),
            width="stretch", hide_index=True,
        )

        # Heatmap
        pivot = display.set_index("Player")[metric_display_cols].astype(float)
        fig = px.imshow(pivot, color_continuous_scale="RdBu_r", zmin=-3, zmax=3,
                        labels=dict(color="Z"), title="Z-Score Heatmap")
        fig = style_chart(fig, height=max(280, len(pivot) * 22))
        st.plotly_chart(fig, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# TOP PERFORMERS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    section_header("Top Performers", icon="🏅",
                   help_text=(
                       "Ranked lists of the squad's best performers for each key metric this season.<br><br>"
                       "These are raw totals or averages, not adjusted for playing time. "
                       "A player who has played 10 matches will naturally have higher totals than one with 4 appearances. "
                       "For fair comparison, use the Player Comparison page which normalises metrics to per-90-minute rates."
                   ))
    metric_opts = {
        "Goals (total)":           ("goals",        "sum"),
        "Assists (total)":         ("assists",       "sum"),
        "xG (total)":              ("xg",           "sum"),
        "xA (total)":              ("xa",           "sum"),
        "Avg Match Rating":        ("match_rating",  "mean"),
        "Avg Distance (m)":        ("distance_m",    "mean"),
        "Avg HSR (m)":             ("hsr_m",         "mean"),
        "Avg Sprint Count":        ("sprint_count",  "mean"),
        "Avg Key Passes":          ("key_passes",    "mean"),
        "Avg Tackles Won":         ("tackles_won",   "mean"),
        "Avg Pressures":           ("pressures",     "mean"),
        "Avg Dribbles Won":        ("dribbles_won",  "mean"),
        "Avg Progressive Passes":  ("progressive_passes","mean"),
        "Avg Touches in Box":      ("touches_in_box","mean"),
    }
    chosen = st.selectbox("Rank by", list(metric_opts.keys()))
    col, fn = metric_opts[chosen]
    top = (match_players.groupby(["player_name", "position"])[col]
           .agg(fn).reset_index()
           .sort_values(col, ascending=False).head(12))
    top.columns = ["Player", "Position", chosen]

    bar_cols = PALETTE[:12]
    fig = go.Figure(go.Bar(
        x=top[chosen], y=top["Player"],
        orientation="h", marker_color=bar_cols,
        text=top[chosen].round(2), textposition="outside",
    ))
    fig = style_chart(fig, height=420,
                      xaxis=dict(title=chosen, gridcolor=COLORS["grid"]),
                      yaxis=dict(autorange="reversed", gridcolor=COLORS["grid"]))
    fig.update_layout(title=f"Top 12 - {chosen}")
    st.plotly_chart(fig, width="stretch")
