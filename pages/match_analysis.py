"""Match Analysis — shot map, xG timeline, pressing stats, player ratings."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, draw_pitch, info_box, create_3d_kpi_dashboard
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

    # Default to showing all attacking positions
    available_pos = sorted(players["position"].unique().tolist())
    default_pos = [p for p in available_pos if p in ['ST', 'LW', 'RW', 'CAM', 'CM']]

    pos_filter = st.multiselect(
        "Filter Shot Map by Position",
        available_pos,
        default=default_pos,
        help="Select positions to see their shots. Defaults to attacking players (ST, LW, RW, CAM, CM)"
    )

match_row  = matches[matches["match_id"] == mid].iloc[0]
mp         = match_players[match_players["match_id"] == mid]
ev         = events[events["match_id"] == mid] if not events.empty else pd.DataFrame()

# Filter by selected positions (always apply filter if data exists)
if not ev.empty and pos_filter:
    shots = ev[ev["position"].isin(pos_filter)].copy()
else:
    shots = ev.copy() if not ev.empty else pd.DataFrame()

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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["🗺️ Shot Map", "📈 xG Timeline", "👤 Player Ratings", "📊 Match Stats", "🎯 3D KPI Dashboard", "💡 CSF & KPI Guide"])

# ═══════════════════════════════════════════════════════════════════════════════
# SHOT MAP
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("Shot Map", icon="🗺️",
                   subtitle="Attacking left → right · Goal at x=105 · Bubble size = xG value")

    # Show info about filtering
    if pos_filter:
        st.info(f"📍 Showing shots from: {', '.join(pos_filter)} ({len(shots)} shots)")
    else:
        st.warning("No positions selected. Select at least one position in the sidebar.")

    fig = draw_pitch()

    if not shots.empty:
        for subset, label, color, symbol in [
            (shots[shots["goal"] == True],      "Goal",       COLORS["success"], "star"),
            (shots[(shots["on_target"]) & (~shots["goal"])], "On Target", COLORS["warning"], "circle"),
            (shots[~shots["on_target"]],         "Off Target", COLORS["danger"],  "x"),
        ]:
            if subset.empty: continue

            hover_texts = []
            for _, r in subset.iterrows():
                text = f"<b>{r['player_name']}</b><br>"
                text += f"Position: {r['position']}<br>"
                text += f"Minute: {r['minute']}<br>"
                text += f"xG: {r['xg']:.3f}<br>"
                text += f"Location: ({r['x']:.1f}, {r['y']:.1f})<br>"
                if r['on_target']:
                    text += "Status: On Target"
                else:
                    text += "Status: Off Target"
                if r['goal']:
                    text += " ⚽ GOAL"
                hover_texts.append(text)

            # Calculate bubble sizes with better scaling
            # Min size 12, max size 50 based on xG value
            sizes = (subset["xg"] * 35).clip(lower=12) + 8

            fig.add_trace(go.Scatter(
                x=subset["x"], y=subset["y"], mode="markers", name=label,
                marker=dict(
                    size=sizes,
                    color=color, symbol=symbol, opacity=0.85,
                    line=dict(width=2, color=COLORS["bg"]),
                ),
                text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
            ))
    st.plotly_chart(fig, width="stretch")

    if not shots.empty:
        # Shot summary
        goals_count = int(shots["goal"].sum())
        on_target_count = int(shots["on_target"].sum())
        off_target_count = len(shots) - on_target_count

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Shots", len(shots))
        with col2:
            st.metric("Goals ⚽", goals_count)
        with col3:
            st.metric("On Target 🎯", on_target_count)
        with col4:
            st.metric("Off Target ❌", off_target_count)

        st.subheader("Shot Details Table")
        shot_tbl = shots[["player_name","position","minute","xg","on_target","goal"]].copy()
        shot_tbl.columns = ["Player","Position","Minute","xG","On Target","Goal"]
        shot_tbl = shot_tbl.sort_values("Minute").reset_index(drop=True)

        # Color code the table based on shot result
        def color_row(row):
            if row['Goal']:
                return ['background-color: #1a3a1a'] * len(row)
            elif row['On Target']:
                return ['background-color: #2a3a1a'] * len(row)
            else:
                return ['background-color: #1a1a1a'] * len(row)

        styled_table = shot_tbl.style.apply(color_row, axis=1)
        st.dataframe(styled_table, width="stretch", hide_index=True)
    else:
        st.info("No shots recorded for this match with selected position filters.")

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
            stats_df = pd.DataFrame({
                "Statistic": [
                    "Total Distance",
                    "High-Speed Running",
                    "Sprint Distance",
                    "Total Sprints",
                    "Accelerations",
                    "Decelerations",
                    "Total Passes",
                    "Pass Completion",
                    "Progressive Passes",
                    "Pressures",
                    "Pressures Won",
                    "Key Passes",
                    "Dribbles Won",
                    "Tackles Won",
                    "Total Shots",
                    "Shots on Target",
                    "Total xG",
                    "Possession",
                    "PPDA",
                ],
                "Value": [
                    f"{mp['distance_m'].sum():,.0f} m",
                    f"{mp['hsr_m'].sum():,.0f} m",
                    f"{mp['sprint_m'].sum():,.0f} m",
                    f"{int(mp['sprint_count'].sum())}",
                    f"{int(mp['accel_count'].sum())}",
                    f"{int(mp['decel_count'].sum())}",
                    f"{int(mp['passes'].sum())}",
                    f"{mp['pass_completion'].mean()*100:.1f}%",
                    f"{int(mp['progressive_passes'].sum())}",
                    f"{int(mp['pressures'].sum())}",
                    f"{int(mp['pressures_won'].sum())}",
                    f"{int(mp['key_passes'].sum())}",
                    f"{int(mp['dribbles_won'].sum())}",
                    f"{int(mp['tackles_won'].sum())}",
                    f"{n_shots}",
                    f"{ot_shots}",
                    f"{total_xg:.3f}",
                    f"{poss:.1f}%",
                    f"{ppda:.1f}",
                ]
            })
            st.dataframe(stats_df, width="stretch", hide_index=True)

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

# ═══════════════════════════════════════════════════════════════════════════════
# 3D KPI DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab5:
    if mp.empty:
        st.info("No player data for 3D visualization.")
    else:
        section_header("3D Player Performance Dashboard", icon="🎯",
                       subtitle="Explore player metrics across three dimensions")

        col1, col2, col3 = st.columns(3)
        with col1:
            x_metric = st.selectbox("X-Axis Metric",
                ["distance_m", "passes", "pressures", "tackles_won", "key_passes",
                 "dribbles_won", "hsr_m", "sprint_count"], key="x_3d")
        with col2:
            y_metric = st.selectbox("Y-Axis Metric",
                ["match_rating", "pass_completion", "pressures_won", "work_rate",
                 "max_speed_kmh", "accel_count", "decel_count"], key="y_3d")
        with col3:
            z_metric = st.selectbox("Z-Axis Metric",
                ["match_rating", "distance_m", "passes", "pressures", "work_rate",
                 "hsr_m", "sprint_count"], key="z_3d")

        try:
            mp_clean = mp[[x_metric, y_metric, z_metric, "position", "player_name"]].dropna().copy()

            if not mp_clean.empty and len(mp_clean) > 0:
                fig_3d = create_3d_kpi_dashboard(
                    mp_clean,
                    x_col=x_metric,
                    y_col=y_metric,
                    z_col=z_metric,
                    color_col="position",
                    title=f"3D Player Performance: {x_metric} vs {y_metric} vs {z_metric}"
                )
                st.plotly_chart(fig_3d, width="stretch")

                st.subheader("Performance Summary by Position")
                summary_stats = []
                for pos in sorted(mp_clean["position"].unique()):
                    pos_data = mp_clean[mp_clean["position"] == pos]
                    try:
                        summary_stats.append({
                            "Position": str(pos),
                            x_metric: float(pos_data[x_metric].mean()),
                            y_metric: float(pos_data[y_metric].mean()),
                            z_metric: float(pos_data[z_metric].mean()),
                        })
                    except (ValueError, TypeError):
                        continue

                if summary_stats:
                    summary_data = pd.DataFrame(summary_stats)
                    st.dataframe(summary_data, width="stretch", hide_index=True)
            else:
                st.info("No player data available for visualization")
        except Exception as e:
            st.error(f"Error: Could not create dashboard. {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# CSF & KPI GUIDE
# ═══════════════════════════════════════════════════════════════════════════════
with tab6:
    section_header("Critical Success Factors & Key Metrics", icon="💡",
                   subtitle="What matters most in football — explained simply")

    col_explain, col_metrics = st.columns([1, 1])

    with col_explain:
        st.markdown("### 📚 What Are CSF & KPI?")
        st.markdown("""
**CSF (Critical Success Factors)** = The few things that MUST go well to win
- Think of it like baking a cake: right temperature, good ingredients, timing

**KPI (Key Performance Indicators)** = Measurable numbers that show if you're doing well
- Like a health check-up: heart rate, blood pressure, weight
        """)

    with col_metrics:
        st.markdown("### ⚽ Match Result")
        result_text = f"{match_row['home_away']} {match_row['goals_for']} – {match_row['goals_against']} {match_row['opponent']}"
        result_color = {"Win": "🟢", "Draw": "🟡", "Loss": "🔴"}.get(match_row["result"], "⚫")
        st.markdown(f"**{result_color} {result_text}**")
        st.markdown(f"**Result:** {match_row['result']}")

    st.divider()

    # KPI Explanations
    st.markdown("## 📊 Key Performance Indicators (Simple Explanation)")

    kpi_explanations = {
        "Goals": {
            "value": match_row["goals_for"],
            "icon": "⚽",
            "simple": "Number of times we scored",
            "why_matters": "More goals = more likely to win",
            "good_level": f"> {int(match_row['goals_for'] + 1)}"
        },
        "Total xG (Expected Goals)": {
            "value": f"{total_xg:.2f}",
            "icon": "🎯",
            "simple": "Quality of our shots (0-1 scale per shot)",
            "why_matters": "Shows if we had good scoring chances (not lucky)",
            "good_level": "> 1.5"
        },
        "Shots": {
            "value": n_shots,
            "icon": "💥",
            "simple": "Total times we tried to score",
            "why_matters": "More attempts = more chances to score",
            "good_level": f"> {int(n_shots + 2)}"
        },
        "Possession": {
            "value": f"{poss:.1f}%",
            "icon": "🔵",
            "simple": "How much we had the ball",
            "why_matters": "More possession = better control of game",
            "good_level": "> 50%"
        },
        "PPDA (Pressing)": {
            "value": f"{ppda:.1f}",
            "icon": "🔥",
            "simple": f"How aggressively we defend (lower = more aggressive)",
            "why_matters": "Aggressive pressing = less time for opponent",
            "good_level": "< 10"
        },
    }

    for title, info in kpi_explanations.items():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown(f"### {info['icon']} {title}")
            st.markdown(f"**Value:** {info['value']}")
        with col2:
            st.markdown(f"**What it means:** {info['simple']}")
            st.markdown(f"**Why it matters:** {info['why_matters']}")
            st.markdown(f"**Good level:** {info['good_level']}")
        st.divider()

    st.markdown("## 🎯 Critical Success Factors")

    # CSF Analysis
    csf_data = []

    # CSF 1: Finishing (Goals vs xG)
    xg_efficiency = (match_row["goals_for"] / total_xg * 100) if total_xg > 0 else 0
    csf_data.append({
        "CSF": "Finishing Quality",
        "icon": "⚽",
        "metric": f"Goals: {match_row['goals_for']} / xG: {total_xg:.2f}",
        "explanation": "Did we score from our chances?",
        "status": "🟢 GOOD" if match_row["goals_for"] >= total_xg * 0.5 else "🟡 OK" if match_row["goals_for"] >= total_xg * 0.2 else "🔴 POOR",
    })

    # CSF 2: Possession Control
    csf_data.append({
        "CSF": "Game Control",
        "icon": "🔵",
        "metric": f"Possession: {poss:.1f}%",
        "explanation": "Did we control the game?",
        "status": "🟢 GOOD" if poss > 55 else "🟡 OK" if poss > 45 else "🔴 POOR",
    })

    # CSF 3: Defensive Strength
    csf_data.append({
        "CSF": "Defensive Strength",
        "icon": "🛡️",
        "metric": f"PPDA: {ppda:.1f} (lower is better)",
        "explanation": "How tight was our defense?",
        "status": "🟢 GOOD" if ppda < 10 else "🟡 OK" if ppda < 13 else "🔴 POOR",
    })

    # CSF 4: Shot Efficiency
    ot_pct = (ot_shots / n_shots * 100) if n_shots > 0 else 0
    csf_data.append({
        "CSF": "Shot Accuracy",
        "icon": "🎯",
        "metric": f"On Target: {ot_shots}/{n_shots} ({ot_pct:.0f}%)",
        "explanation": "Did we aim well at goal?",
        "status": "🟢 GOOD" if ot_pct > 50 else "🟡 OK" if ot_pct > 30 else "🔴 POOR",
    })

    st.markdown("### What Must Go Right to Win 👇")

    for csf in csf_data:
        col1, col2, col3 = st.columns([1.5, 2, 1.5])
        with col1:
            st.markdown(f"**{csf['icon']} {csf['CSF']}**")
        with col2:
            st.markdown(f"*{csf['explanation']}*")
            st.code(csf['metric'], language=None)
        with col3:
            st.markdown(csf['status'])
        st.markdown("---")

    # Match Verdict
    st.markdown("## 🏆 Match Verdict")

    wins = sum([1 for csf in csf_data if "🟢" in csf["status"]])
    total_csf = len(csf_data)

    verdict_col1, verdict_col2 = st.columns([2, 1])
    with verdict_col1:
        st.markdown(f"### {wins}/{total_csf} Critical Factors Were Successful")
        if match_row["result"] == "Win":
            st.success(f"✅ **WON** - We did enough things right!")
        elif match_row["result"] == "Draw":
            st.info(f"🤝 **DREW** - Both teams were balanced")
        else:
            st.error(f"❌ **LOST** - Need to improve these areas")

    with verdict_col2:
        # Simple visualization
        fig_verdict = go.Figure(go.Indicator(
            mode="gauge+number",
            value=wins,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Success Rate"},
            gauge={
                "axis": {"range": [0, total_csf]},
                "bar": {"color": COLORS["primary"]},
                "steps": [
                    {"range": [0, total_csf * 0.33], "color": COLORS["danger"]},
                    {"range": [total_csf * 0.33, total_csf * 0.66], "color": COLORS["warning"]},
                    {"range": [total_csf * 0.66, total_csf], "color": COLORS["success"]},
                ],
            },
        ))
        fig_verdict.update_layout(height=300, margin=dict(l=0, r=0, t=50, b=0),
                                 paper_bgcolor=COLORS["bg"], font=dict(color=COLORS["text"]))
        st.plotly_chart(fig_verdict, width="stretch")

    st.divider()

    st.markdown("""
### 💡 Quick Tips to Understand Football Analytics

1. **Goals are the result** - Everything else affects whether you score
2. **xG shows luck** - If xG > Goals, you were unlucky. If Goals > xG, you were lucky
3. **Possession doesn't guarantee wins** - But helps you control the game
4. **Pressing is balance** - Too aggressive = exposed defense. Too passive = no pressure
5. **Efficiency matters** - 1 great chance > 10 poor chances

Think of it like a restaurant:
- **CSF** = Must have: good food, clean place, friendly staff
- **KPI** = Numbers we measure: customer count, profit, satisfaction score
    """)
