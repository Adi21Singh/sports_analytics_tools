"""Dashboard — season overview, squad fitness status, recent form."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, info_box
from data.generator import load_data, SEASON_START, SEASON_END, TEAM_NAME
from config import COLORS, PALETTE

styles.apply()

# ── Data ──────────────────────────────────────────────────────────────────────
players, training, wellness, matches, match_players, events = load_data()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"⚽ {TEAM_NAME}")
st.caption(f"Season {SEASON_START.strftime('%b %Y')} – {SEASON_END.strftime('%b %Y')} · Sports Analytics Platform")
st.divider()

# ── Season KPIs ───────────────────────────────────────────────────────────────
wins   = int((matches["result"] == "Win").sum())
draws  = int((matches["result"] == "Draw").sum())
losses = int((matches["result"] == "Loss").sum())
gf     = int(matches["goals_for"].sum())
ga     = int(matches["goals_against"].sum())
pts    = wins * 3 + draws
win_pct = wins / len(matches) * 100
avg_poss = matches["possession_pct"].mean()
avg_ppda = matches["ppda"].mean()

section_header("Season Overview", icon="📋")
kpi_row([
    kpi_card("Points",           pts,              sub=f"{wins}W  {draws}D  {losses}L",  accent=COLORS["primary"]),
    kpi_card("Win Rate",         f"{win_pct:.0f}%",sub=f"{len(matches)} matches played",  accent=COLORS["success"]),
    kpi_card("Goals For",        gf,               sub=f"GD {gf - ga:+d}",               accent=COLORS["secondary"]),
    kpi_card("Goals Against",    ga,               sub=f"Avg {ga/len(matches):.1f} per match", accent=COLORS["danger"]),
    kpi_card("Avg Possession",   f"{avg_poss:.1f}%",sub="Season average",                accent=COLORS["warning"]),
    kpi_card("Avg PPDA",         f"{avg_ppda:.1f}",sub="Lower = more pressing",          accent=COLORS["primary"]),
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Squad fitness KPIs ────────────────────────────────────────────────────────
from analytics.load_monitoring import calculate_acwr
from config import acwr_zone

risk_counts = {"Optimal": 0, "Caution": 0, "High Risk": 0, "Under-training": 0}
for _, pl in players.iterrows():
    p_load = training[training["player_id"] == pl["id"]]
    if p_load.empty:
        continue
    acwr_df = calculate_acwr(p_load["srpe"], p_load["date"])
    zone = acwr_zone(float(acwr_df["acwr"].iloc[-1]))
    risk_counts[zone] = risk_counts.get(zone, 0) + 1

max_sessions = training.groupby("player_id").size().max()
avg_availability = (
    training.groupby("player_id").size() / max_sessions * 100
).mean()

section_header("Squad Readiness", icon="⚕️")
kpi_row([
    kpi_card("Available (Optimal)", risk_counts["Optimal"],      accent=COLORS["success"]),
    kpi_card("Monitor (Caution)",   risk_counts["Caution"],      accent=COLORS["warning"]),
    kpi_card("Flag (High Risk)",    risk_counts["High Risk"],     accent=COLORS["danger"]),
    kpi_card("Avg Availability",    f"{avg_availability:.0f}%",  accent=COLORS["primary"]),
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Two-column row ────────────────────────────────────────────────────────────
left, right = st.columns([3, 2])

with left:
    section_header("Season Results Timeline", icon="📈")
    df_m = matches.sort_values("date").copy()
    df_m["match_no"] = range(1, len(df_m) + 1)
    df_m["cum_pts"]  = df_m["result"].map({"Win": 3, "Draw": 1, "Loss": 0}).cumsum()

    color_map = {"Win": COLORS["success"], "Draw": COLORS["warning"], "Loss": COLORS["danger"]}
    fig = go.Figure()
    for res, color in color_map.items():
        mask = df_m["result"] == res
        fig.add_trace(go.Bar(
            x=df_m[mask]["match_no"], y=df_m[mask]["goals_for"],
            name=res, marker_color=color, opacity=0.85,
            customdata=df_m[mask][["opponent", "goals_against", "possession_pct"]].values,
            hovertemplate="<b>%{customdata[0]}</b><br>%{y} – %{customdata[1]}<br>Poss: %{customdata[2]:.1f}%<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=df_m["match_no"], y=df_m["cum_pts"],
        mode="lines", name="Cumulative Pts",
        line=dict(color=COLORS["primary"], width=2.5, dash="dot"),
        yaxis="y2",
    ))
    fig = style_chart(fig, height=300,
                      yaxis=dict(title="Goals", gridcolor=COLORS["grid"]),
                      yaxis2=dict(title="Pts", overlaying="y", side="right", showgrid=False),
                      barmode="overlay", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig, width="stretch")

with right:
    section_header("Top Scorers", icon="⚽")
    top = (match_players.groupby(["player_name", "position"])
           .agg(goals=("goals", "sum"), xg=("xg", "sum"))
           .reset_index()
           .sort_values("goals", ascending=False)
           .head(8))
    fig2 = go.Figure(go.Bar(
        x=top["goals"], y=top["player_name"],
        orientation="h", marker_color=COLORS["primary"],
        text=top["goals"], textposition="outside",
        customdata=top["xg"].round(2),
        hovertemplate="%{y}<br>Goals: %{x}<br>xG: %{customdata}<extra></extra>",
    ))
    fig2 = style_chart(fig2, height=300,
                       yaxis=dict(autorange="reversed", gridcolor=COLORS["grid"]),
                       xaxis=dict(title="Goals", gridcolor=COLORS["grid"]))
    st.plotly_chart(fig2, width="stretch")

# ── Bottom row ────────────────────────────────────────────────────────────────
b1, b2 = st.columns(2)

with b1:
    section_header("Avg Distance by Position", icon="🏃")
    avg_dist = (training.groupby("position")["distance_m"].mean()
                .reset_index().sort_values("distance_m", ascending=True))
    fig3 = go.Figure(go.Bar(
        x=avg_dist["distance_m"], y=avg_dist["position"],
        orientation="h", marker_color=PALETTE[:len(avg_dist)],
        text=avg_dist["distance_m"].round(0).astype(int).map(lambda v: f"{v:,}m"),
        textposition="outside",
    ))
    fig3 = style_chart(fig3, height=280,
                       xaxis=dict(title="Avg Distance (m)", gridcolor=COLORS["grid"]),
                       yaxis=dict(gridcolor=COLORS["grid"]))
    st.plotly_chart(fig3, width="stretch")

with b2:
    section_header("Result Distribution", icon="🥇")
    counts = matches["result"].value_counts().reset_index()
    counts.columns = ["Result", "Count"]
    color_order = [color_map.get(r, "#aaa") for r in counts["Result"]]
    fig4 = go.Figure(go.Pie(
        labels=counts["Result"], values=counts["Count"],
        marker=dict(colors=color_order),
        hole=0.55, textinfo="label+percent",
    ))
    fig4 = style_chart(fig4, height=280)
    fig4.update_traces(textfont_color=COLORS["text"])
    st.plotly_chart(fig4, width="stretch")

st.divider()
st.caption("MIS41500 Sports & Performance Analytics · Group Assessment")
