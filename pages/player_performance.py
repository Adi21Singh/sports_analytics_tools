"""Player Performance — physical KPIs, technical stats, wellness, radar profile."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, empty_state, info_box
from data.generator import load_data
from analytics.performance import build_radar_profile, compute_derived_kpis, RADAR_METRICS
from config import COLORS, PALETTE

styles.apply()

players, training, wellness, matches, match_players, events = load_data()
match_players = compute_derived_kpis(match_players)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Player Performance")
    name = st.selectbox("Player", sorted(players["name"].tolist()))
    row  = players[players["name"] == name].iloc[0]
    pid  = int(row["id"])

    min_d = training["date"].min().date()
    max_d = training["date"].max().date()
    dates = st.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)
    d0 = pd.Timestamp(dates[0] if len(dates) > 0 else min_d)
    d1 = pd.Timestamp(dates[1] if len(dates) > 1 else max_d)

    roll_w = st.slider("Trend Window (matches)", 3, 10, 5)

# ── Filters ───────────────────────────────────────────────────────────────────
p_train = training[(training["player_id"] == pid) &
                   (training["date"] >= d0) & (training["date"] <= d1)].sort_values("date")
p_match = match_players[match_players["player_id"] == pid].sort_values("date")
p_well  = wellness[(wellness["player_id"] == pid) &
                   (wellness["date"] >= d0) & (wellness["date"] <= d1)].sort_values("date")

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"📊 {name}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Position", row["position"])
c2.metric("Age",      row["age"])
c3.metric("Shirt #",  row["number"])
c4.metric("Matches",  len(p_match))
st.divider()

tab_phys, tab_tech, tab_well, tab_radar = st.tabs(
    ["🏃 Physical", "⚽ Technical", "💊 Wellness", "🕸 Radar Profile"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_phys:
    if p_train.empty:
        empty_state(); st.stop()

    section_header("Physical KPIs — Training Sessions", icon="📐")
    kpi_row([
        kpi_card("Avg Distance",    f"{p_train['distance_m'].mean():,.0f} m",   accent=COLORS["primary"]),
        kpi_card("Avg HSR",         f"{p_train['hsr_m'].mean():,.0f} m",        accent=COLORS["secondary"]),
        kpi_card("Avg Sprint Dist", f"{p_train['sprint_m'].mean():,.0f} m",     accent=COLORS["warning"]),
        kpi_card("Peak Speed",      f"{p_train['max_speed_kmh'].max():.1f} km/h",accent=COLORS["danger"]),
        kpi_card("Avg Work Rate",   f"{p_train['work_rate'].mean():.1f} m/min", accent=COLORS["success"]),
        kpi_card("Avg HML",         f"{p_train['hml_m'].mean():,.0f} m",        accent=COLORS["primary"]),
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # Distance trend + rolling average
    fig = go.Figure()
    fig.add_trace(go.Bar(x=p_train["date"], y=p_train["distance_m"],
                         name="Distance", marker_color=COLORS["secondary"], opacity=0.45))
    roll = p_train["distance_m"].rolling(7, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=p_train["date"], y=roll,
                             mode="lines", name="7-day MA",
                             line=dict(color=COLORS["primary"], width=2.5)))
    fig = style_chart(fig, height=270, yaxis=dict(title="Distance (m)", gridcolor=COLORS["grid"]))
    fig.update_layout(title="Total Distance per Session", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns(2)
    with left:
        # HSR + Sprint stacked area
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=p_train["date"], y=p_train["hsr_m"],
                                  fill="tozeroy", name="HSR (>19.8 km/h)",
                                  line=dict(color=COLORS["secondary"], width=1.5),
                                  fillcolor=f"rgba(124,131,253,0.18)"))
        fig2.add_trace(go.Scatter(x=p_train["date"], y=p_train["sprint_m"],
                                  fill="tozeroy", name="Sprint (>25.2 km/h)",
                                  line=dict(color=COLORS["warning"], width=1.5),
                                  fillcolor=f"rgba(245,158,11,0.25)"))
        fig2 = style_chart(fig2, height=240, yaxis=dict(title="m", gridcolor=COLORS["grid"]))
        fig2.update_layout(title="High-Speed Running Breakdown")
        st.plotly_chart(fig2, width="stretch")

    with right:
        # Accelerations & decelerations
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=p_train["date"], y=p_train["accel_count"],
                                  mode="lines", name="Accelerations",
                                  line=dict(color=COLORS["primary"], width=2)))
        fig3.add_trace(go.Scatter(x=p_train["date"], y=p_train["decel_count"],
                                  mode="lines", name="Decelerations",
                                  line=dict(color=COLORS["danger"], width=2, dash="dot")))
        fig3 = style_chart(fig3, height=240, yaxis=dict(title="Count", gridcolor=COLORS["grid"]))
        fig3.update_layout(title="Acceleration / Deceleration Counts")
        st.plotly_chart(fig3, width="stretch")

    # Load vs RPE scatter
    fig4 = px.scatter(p_train, x="player_load", y="rpe",
                      color="session_type", size="hml_m",
                      color_discrete_sequence=PALETTE,
                      hover_data=["date", "duration_min", "work_rate"],
                      labels={"player_load": "Player Load (AU)", "rpe": "RPE (1–10)",
                              "session_type": "Session"})
    fig4 = style_chart(fig4, height=270)
    fig4.update_layout(title="Session Load vs Perceived Exertion  (bubble = HML distance)")
    st.plotly_chart(fig4, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# TECHNICAL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_tech:
    if p_match.empty:
        empty_state(); st.stop()

    total_xg    = p_match["xg"].sum()
    total_xa    = p_match["xa"].sum()
    goals_total = int(p_match["goals"].sum())
    assts_total = int(p_match["assists"].sum())
    avg_rating  = p_match["match_rating"].mean()
    avg_pass_c  = p_match["pass_completion"].mean() * 100
    avg_xg90    = p_match["xg_p90"].mean()

    section_header("Technical KPIs — Match Data", icon="📐")
    kpi_row([
        kpi_card("Goals",          goals_total,            accent=COLORS["primary"]),
        kpi_card("Assists",        assts_total,            accent=COLORS["success"]),
        kpi_card("Total xG",       f"{total_xg:.2f}",      accent=COLORS["secondary"]),
        kpi_card("Total xA",       f"{total_xa:.2f}",      accent=COLORS["warning"]),
        kpi_card("xG per 90",      f"{avg_xg90:.2f}",      accent=COLORS["danger"]),
        kpi_card("Avg Rating",     f"{avg_rating:.2f}",    accent=COLORS["primary"]),
    ])

    kpi_row([
        kpi_card("Pass Acc%",      f"{avg_pass_c:.1f}%",   accent=COLORS["secondary"]),
        kpi_card("Dribble Succ%",  f"{p_match['dribble_success_rate'].mean()*100:.0f}%", accent=COLORS["primary"]),
        kpi_card("Tackle Succ%",   f"{p_match['tackle_success_rate'].mean()*100:.0f}%",  accent=COLORS["warning"]),
        kpi_card("Aerial Win%",    f"{p_match['aerial_win_rate'].mean()*100:.0f}%",      accent=COLORS["success"]),
        kpi_card("Press Succ%",    f"{p_match['press_success_rate'].mean()*100:.0f}%",   accent=COLORS["danger"]),
        kpi_card("Goal Inv/90",    f"{p_match['goal_involvement_p90'].mean():.2f}",      accent=COLORS["primary"]),
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    # Rating trend
    p_match_s = p_match.sort_values("date").reset_index(drop=True)
    p_match_s["rolling_rating"] = p_match_s["match_rating"].rolling(roll_w, min_periods=1).mean()
    p_match_s["rolling_xg"]     = p_match_s["xg"].rolling(roll_w, min_periods=1).sum()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=p_match_s["date"], y=p_match_s["match_rating"],
                         name="Match Rating", marker_color=COLORS["secondary"], opacity=0.5))
    fig.add_trace(go.Scatter(x=p_match_s["date"], y=p_match_s["rolling_rating"],
                             mode="lines", name=f"{roll_w}-match MA",
                             line=dict(color=COLORS["primary"], width=2.5)))
    fig.add_hline(y=7.0, line_dash="dash", line_color=COLORS["muted"], line_width=1,
                  annotation_text="7.0 benchmark", annotation_font_color=COLORS["muted"])
    fig = style_chart(fig, height=270, yaxis=dict(range=[4.5, 10], title="Rating",
                                                   gridcolor=COLORS["grid"]))
    fig.update_layout(title="Match Rating Trend", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, width="stretch")

    l, r = st.columns(2)
    with l:
        # Goals + assists
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(x=p_match_s["date"], y=p_match_s["goals"],
                              name="Goals", marker_color=COLORS["primary"]))
        fig2.add_trace(go.Bar(x=p_match_s["date"], y=p_match_s["assists"],
                              name="Assists", marker_color=COLORS["warning"]))
        fig2 = style_chart(fig2, height=240, barmode="stack",
                           yaxis=dict(title="Count", gridcolor=COLORS["grid"]))
        fig2.update_layout(title="Goals & Assists by Match")
        st.plotly_chart(fig2, width="stretch")
    with r:
        # Key technical averages
        tech_avgs = {
            "Passes": p_match["passes"].mean(),
            "Key Passes": p_match["key_passes"].mean(),
            "Prog. Passes": p_match["progressive_passes"].mean(),
            "Dribbles Won": p_match["dribbles_won"].mean(),
            "Pressures": p_match["pressures"].mean(),
            "Touches Box": p_match["touches_in_box"].mean(),
        }
        fig3 = go.Figure(go.Bar(
            x=list(tech_avgs.values()), y=list(tech_avgs.keys()),
            orientation="h", marker_color=PALETTE[:len(tech_avgs)],
            text=[f"{v:.1f}" for v in tech_avgs.values()], textposition="outside",
        ))
        fig3 = style_chart(fig3, height=240,
                           xaxis=dict(title="Avg per match", gridcolor=COLORS["grid"]),
                           yaxis=dict(gridcolor=COLORS["grid"]))
        fig3.update_layout(title="Technical Output per Match")
        st.plotly_chart(fig3, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# WELLNESS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_well:
    if p_well.empty:
        empty_state("No wellness data in selected period.")
    else:
        avg_comp   = p_well["wellness_composite"].mean()
        avg_sleep  = p_well["sleep_score"].mean()
        avg_fat    = p_well["fatigue_score"].mean()
        avg_sor    = p_well["soreness_score"].mean()
        avg_mood   = p_well["mood_score"].mean()

        section_header("Wellness Overview", icon="💊")
        kpi_row([
            kpi_card("Composite Score",  f"{avg_comp:.1f}/10", accent=COLORS["primary"]),
            kpi_card("Avg Sleep",        f"{avg_sleep:.1f}/10", accent=COLORS["success"]),
            kpi_card("Avg Fatigue",      f"{avg_fat:.1f}/10",   accent=COLORS["danger"]),
            kpi_card("Avg Soreness",     f"{avg_sor:.1f}/10",   accent=COLORS["warning"]),
            kpi_card("Avg Mood",         f"{avg_mood:.1f}/10",  accent=COLORS["secondary"]),
        ])
        st.markdown("<br>", unsafe_allow_html=True)

        info_box("Composite Wellness = (Sleep + (10−Fatigue) + (10−Soreness) + Mood + (10−Stress)) / 5 — higher is better readiness.")

        fig = go.Figure()
        roll = p_well["wellness_composite"].rolling(7, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=p_well["date"], y=p_well["wellness_composite"],
                                 mode="markers", name="Daily", marker=dict(color=COLORS["muted"], size=4)))
        fig.add_trace(go.Scatter(x=p_well["date"], y=roll,
                                 mode="lines", name="7-day MA",
                                 line=dict(color=COLORS["primary"], width=2.5)))
        fig.add_hline(y=6.0, line_dash="dash", line_color=COLORS["warning"], line_width=1,
                      annotation_text="Low readiness threshold")
        fig = style_chart(fig, height=270, yaxis=dict(range=[2, 10], title="Score",
                                                       gridcolor=COLORS["grid"]))
        fig.update_layout(title="Composite Wellness Score (higher = better readiness)")
        st.plotly_chart(fig, width="stretch")

        # Component breakdown
        comp_map = {"Sleep": "sleep_score", "Fatigue (inv)": "fatigue_score",
                    "Soreness (inv)": "soreness_score", "Mood": "mood_score"}
        comp_fig = go.Figure()
        for label, col in comp_map.items():
            vals = p_well[col].rolling(7, min_periods=1).mean()
            comp_fig.add_trace(go.Scatter(x=p_well["date"], y=vals, mode="lines",
                                          name=label, line=dict(width=1.8)))
        comp_fig = style_chart(comp_fig, height=260,
                               yaxis=dict(range=[1, 10], title="Score (1–10)",
                                          gridcolor=COLORS["grid"]))
        comp_fig.update_layout(title="Wellness Components (7-day MA)")
        st.plotly_chart(comp_fig, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# RADAR PROFILE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_radar:
    radar = build_radar_profile(pid, match_players)
    if not radar:
        empty_state("No match data to build profile.")
    else:
        labels = [RADAR_METRICS[k] for k in radar]
        pcts   = [radar[k]["percentile"] for k in radar]
        pcts_c = pcts + [pcts[0]]
        labs_c = labels + [labels[0]]

        fig = go.Figure(go.Scatterpolar(
            r=pcts_c, theta=labs_c, fill="toself",
            fillcolor=f"rgba(0,199,168,0.15)",
            line=dict(color=COLORS["primary"], width=2.5),
            name=name,
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
            showlegend=False,
            paper_bgcolor=COLORS["bg"],
            height=480,
            margin=dict(t=60, b=40),
            title=dict(text=f"{name} — Squad Percentile Profile", font=dict(color=COLORS["text"])),
        )
        st.plotly_chart(fig, width="stretch")

        # Percentile bar chart
        pct_df = pd.DataFrame({"Metric": labels, "Percentile": pcts}).sort_values("Percentile")
        bar_colors = [
            COLORS["success"] if p >= 67 else COLORS["warning"] if p >= 33 else COLORS["danger"]
            for p in pct_df["Percentile"]
        ]
        fig2 = go.Figure(go.Bar(
            x=pct_df["Percentile"], y=pct_df["Metric"],
            orientation="h", marker_color=bar_colors,
            text=[f"{p:.0f}th" for p in pct_df["Percentile"]], textposition="outside",
        ))
        fig2.add_vline(x=50, line_dash="dash", line_color=COLORS["muted"],
                       annotation_text="Squad Median", annotation_font_color=COLORS["muted"])
        fig2 = style_chart(fig2, height=380,
                           xaxis=dict(range=[0, 110], title="Percentile Rank",
                                      gridcolor=COLORS["grid"]),
                           yaxis=dict(gridcolor=COLORS["grid"]))
        fig2.update_layout(title="Percentile vs Full Squad  (green = top · red = bottom)")
        st.plotly_chart(fig2, width="stretch")
