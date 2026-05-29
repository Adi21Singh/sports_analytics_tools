"""Match Analysis — shot map, xG timeline, pressing stats, player ratings."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, draw_pitch, info_box
from ui.data_source import render_data_source_selector, get_data
from analytics.performance import compute_derived_kpis
from config import COLORS, PALETTE

styles.apply()

# ── Sidebar phase 1 — data source ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚽ Match Analysis")
    render_data_source_selector()

players, training, wellness, matches, match_players, events = get_data()
match_players = compute_derived_kpis(match_players)

# ── Sidebar phase 2 — match / position controls ───────────────────────────────
with st.sidebar:
    labels = [f"M{r['match_id']:02d}  vs {r['opponent']}  ({r['result']})"
              for _, r in matches.sort_values("date").iterrows()]
    sel = st.selectbox("Select Match", labels)
    mid = int(sel.split("M")[1].split(" ")[0])

    pos_filter = st.multiselect(
        "Filter Shot Map by Position",
        sorted(players["position"].unique().tolist()),
    )

match_row  = matches[matches["match_id"] == mid].iloc[0]
mp         = match_players[match_players["match_id"] == mid]
ev         = events[events["match_id"] == mid] if not events.empty else pd.DataFrame()
shots      = ev[ev["position"].isin(pos_filter)] if (not ev.empty and pos_filter) else ev

# ── Header ────────────────────────────────────────────────────────────────────
result_color = {"Win": COLORS["success"], "Draw": COLORS["warning"], "Loss": COLORS["danger"]}
res_col = result_color.get(match_row["result"], COLORS["muted"])

st.title("⚽ Match Analysis")
st.markdown(
    f"<h3 style='color:{COLORS['text']};'>"
    f"{match_row['home_away']} vs <b>{match_row['opponent']}</b></h3>"
    f"<span style='color:{COLORS['muted']};font-size:.9rem;'>"
    f"{match_row['date'].strftime('%d %b %Y')}</span>"
    f"  <span style='font-size:1.5rem; font-weight:700; color:{res_col};'>"
    f"{match_row['goals_for']} – {match_row['goals_against']}</span>"
    f"  <span style='color:{res_col};font-size:.9rem;'>({match_row['result']})</span>",
    unsafe_allow_html=True,
)
st.divider()

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_xg = float(shots["xg"].sum()) if not shots.empty else 0.0
n_shots  = len(shots)
ot_shots = int(shots["on_target"].sum()) if not shots.empty else 0
avg_rat  = mp["match_rating"].mean() if not mp.empty else 0.0
poss     = match_row["possession_pct"]
ppda     = match_row["ppda"]

kpi_row([
    kpi_card("Goals",       match_row["goals_for"],   accent=COLORS["success"]),
    kpi_card("Total xG",    f"{total_xg:.2f}",        accent=COLORS["primary"]),
    kpi_card("Shots",       n_shots,                  accent=COLORS["secondary"]),
    kpi_card("On Target",   ot_shots,                 accent=COLORS["warning"]),
    kpi_card("Possession",  f"{poss:.1f}%",           accent=COLORS["primary"]),
    kpi_card("PPDA",        f"{ppda:.1f}",            sub="lower = more pressing", accent=COLORS["danger"]),
    kpi_card("Avg Rating",  f"{avg_rat:.2f}",         accent=COLORS["success"]),
])
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(
    ["🗺️ Shot Map", "📈 xG Timeline", "👤 Player Ratings", "📊 Match Stats"])

# ═══════════════════════════════════════════════════════════════════════════════
# SHOT MAP
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("Shot Map", icon="🗺️",
                   subtitle="Attacking left → right · Goal at x=105 · Bubble size = xG value")
    fig = draw_pitch()

    if not shots.empty:
        for subset, label, color, symbol in [
            (shots[shots["goal"] == True],      "Goal",       COLORS["success"], "star"),
            (shots[(shots["on_target"]) & (~shots["goal"])], "On Target", COLORS["warning"], "circle"),
            (shots[~shots["on_target"]],         "Off Target", COLORS["danger"],  "x"),
        ]:
            if subset.empty: continue
            fig.add_trace(go.Scatter(
                x=subset["x"], y=subset["y"], mode="markers", name=label,
                marker=dict(
                    size=subset["xg"] * 45 + 7,
                    color=color, symbol=symbol, opacity=0.88,
                    line=dict(width=1, color=COLORS["bg"]),
                ),
                text=[f"{r['player_name']}<br>xG: {r['xg']:.3f}<br>Min {r['minute']}"
                      for _, r in subset.iterrows()],
                hovertemplate="%{text}<extra></extra>",
            ))
    st.plotly_chart(fig, width="stretch")

    if not shots.empty:
        st.subheader("Shot Details")
        shot_tbl = shots[["player_name","position","minute","xg","on_target","goal"]].copy()
        shot_tbl.columns = ["Player","Position","Minute","xG","On Target","Goal"]
        st.dataframe(shot_tbl.sort_values("Minute"), width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# xG TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("xG Timeline", icon="📈")
    info_box(
        "Expected Goals (xG) = logistic function of shot distance and angle to goal. "
        "Each shot adds its xG to the cumulative total, giving a 'fair-score' view of the match."
    )

    if shots.empty:
        st.info("No shot events for this match.")
    else:
        s_sorted = shots.sort_values("minute").copy()
        s_sorted["cum_xg"] = s_sorted["xg"].cumsum()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=s_sorted["minute"], y=s_sorted["cum_xg"],
            mode="lines+markers", name="Cumulative xG",
            line=dict(color=COLORS["primary"], width=2.5, shape="hv"),
            marker=dict(size=s_sorted["xg"] * 30 + 5, color=COLORS["primary"],
                        symbol=["star" if g else "circle" for g in s_sorted["goal"]]),
            text=[f"{r['player_name']}<br>xG {r['xg']:.3f}" for _, r in s_sorted.iterrows()],
            hovertemplate="%{text}<br>Min %{x}<extra></extra>",
        ))
        for _, gr in s_sorted[s_sorted["goal"]].iterrows():
            fig.add_vline(x=gr["minute"], line_dash="dash", line_color=COLORS["success"], opacity=0.7)
            fig.add_annotation(x=gr["minute"], y=gr["cum_xg"],
                               text=f"⚽ {gr['player_name']}", showarrow=True,
                               font=dict(color=COLORS["success"], size=10), ax=20, ay=-30)
        fig.add_hline(y=total_xg, line_dash="dot", line_color=COLORS["muted"],
                      annotation_text=f"Total xG {total_xg:.2f}",
                      annotation_font_color=COLORS["muted"])
        fig = style_chart(fig, height=360,
                          xaxis=dict(range=[0, 95], title="Minute", gridcolor=COLORS["grid"]),
                          yaxis=dict(title="Cumulative xG", gridcolor=COLORS["grid"]))
        st.plotly_chart(fig, width="stretch")

        # xG per player
        xg_p = shots.groupby("player_name").agg(
            Shots=("xg","count"), xG=("xg","sum"), Goals=("goal","sum")
        ).reset_index().sort_values("xG", ascending=False)
        xg_p["xG"] = xg_p["xG"].round(3)
        st.dataframe(xg_p, width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER RATINGS
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    if mp.empty:
        st.info("No player data.")
    else:
        section_header("Player Match Ratings", icon="👤")
        mp_s = mp.sort_values("match_rating", ascending=False)
        bar_c = [COLORS["success"] if r >= 7.5 else COLORS["warning"] if r >= 6.5 else COLORS["danger"]
                 for r in mp_s["match_rating"]]
        fig = go.Figure(go.Bar(
            x=mp_s["match_rating"], y=mp_s["player_name"],
            orientation="h", marker_color=bar_c,
            text=[f"{r:.1f}" for r in mp_s["match_rating"]], textposition="outside",
        ))
        fig.add_vline(x=7.0, line_dash="dash", line_color=COLORS["muted"])
        fig = style_chart(fig, height=max(280, len(mp_s)*24),
                          xaxis=dict(range=[4, 10.5], title="Rating", gridcolor=COLORS["grid"]),
                          yaxis=dict(autorange="reversed"))
        fig.update_layout(title="Match Ratings  (green ≥ 7.5 · yellow ≥ 6.5 · red < 6.5)",
                          margin=dict(l=150))
        st.plotly_chart(fig, width="stretch")

        section_header("Physical Output", icon="🏃")
        phys = mp[["player_name","position","minutes_played","distance_m",
                   "hsr_m","sprint_count","max_speed_kmh","work_rate"]].sort_values("distance_m", ascending=False)
        phys.columns = ["Player","Pos","Mins","Distance (m)","HSR (m)",
                        "Sprints","Max Speed (km/h)","Work Rate (m/min)"]
        st.dataframe(phys, width="stretch", hide_index=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MATCH STATS
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    if mp.empty:
        st.info("No data.")
    else:
        l, r = st.columns([1, 1])
        with l:
            section_header("Team Statistics", icon="📊")
            stats = [
                ("Total Distance",      f"{mp['distance_m'].sum():,.0f} m"),
                ("High-Speed Running",  f"{mp['hsr_m'].sum():,.0f} m"),
                ("Sprint Distance",     f"{mp['sprint_m'].sum():,.0f} m"),
                ("Total Sprints",       mp["sprint_count"].sum()),
                ("Accelerations",       mp["accel_count"].sum()),
                ("Decelerations",       mp["decel_count"].sum()),
                ("Total Passes",        mp["passes"].sum()),
                ("Pass Completion",     f"{mp['pass_completion'].mean()*100:.1f}%"),
                ("Progressive Passes",  mp["progressive_passes"].sum()),
                ("Pressures",           mp["pressures"].sum()),
                ("Pressures Won",       mp["pressures_won"].sum()),
                ("Key Passes",          mp["key_passes"].sum()),
                ("Dribbles Won",        mp["dribbles_won"].sum()),
                ("Tackles Won",         mp["tackles_won"].sum()),
                ("Total Shots",         n_shots),
                ("Shots on Target",     ot_shots),
                ("Total xG",            f"{total_xg:.3f}"),
                ("Possession",          f"{poss:.1f}%"),
                ("PPDA",                f"{ppda:.1f}"),
            ]
            st.dataframe(pd.DataFrame(stats, columns=["Statistic", "Value"]),
                         width="stretch", hide_index=True)

        with r:
            section_header("Distance by Position", icon="🏃")
            pos_d = mp.groupby("position")["distance_m"].sum().reset_index().sort_values("distance_m")
            fig = go.Figure(go.Bar(
                x=pos_d["distance_m"], y=pos_d["position"],
                orientation="h", marker_color=PALETTE[:len(pos_d)],
                text=pos_d["distance_m"].map(lambda v: f"{v:,.0f}m"), textposition="outside",
            ))
            fig = style_chart(fig, height=260,
                              xaxis=dict(title="Total Distance (m)", gridcolor=COLORS["grid"]))
            fig.update_layout(margin=dict(l=60))
            st.plotly_chart(fig, width="stretch")

            # Pressing by position
            section_header("Pressures by Position", icon="🔥")
            pos_p = mp.groupby("position")[["pressures","pressures_won"]].sum().reset_index()
            pos_p["success_rate"] = (pos_p["pressures_won"] / pos_p["pressures"] * 100).round(1)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=pos_p["position"], y=pos_p["pressures"],
                                  name="Total", marker_color=COLORS["secondary"], opacity=0.7))
            fig2.add_trace(go.Bar(x=pos_p["position"], y=pos_p["pressures_won"],
                                  name="Won", marker_color=COLORS["primary"]))
            fig2 = style_chart(fig2, height=240, barmode="group",
                               yaxis=dict(title="Count", gridcolor=COLORS["grid"]))
            fig2.update_layout(title="Pressing Volume")
            st.plotly_chart(fig2, width="stretch")
