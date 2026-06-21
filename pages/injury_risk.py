"""Injury & Load Monitor - ACWR, PMC, monotony, ML risk prediction."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, info_box, risk_badge, info_popover
from ui.data_source import render_data_source_selector, get_data
from analytics.load_monitoring import (
    calculate_acwr, calculate_pmc, calculate_monotony_strain, availability_pct
)
from analytics.risk_model import predict_squad_risk
from config import COLORS, PALETTE, ACWR_ZONES, acwr_zone

styles.apply()

# ── Sidebar phase 1 - data source ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚕️ Injury & Load Monitor")
    render_data_source_selector()

players, training, wellness, matches, match_players, events = get_data()

# ── Sidebar phase 2 - player / window controls ────────────────────────────────
with st.sidebar:
    name = st.selectbox("Individual Player", sorted(players["name"].tolist()))
    row  = players[players["name"] == name].iloc[0]
    pid  = int(row["id"])

    acute_d   = st.slider("Acute Window (days)",   5, 10, 7)
    chronic_d = st.slider("Chronic Window (days)", 21, 42, 28)

p_train = training[training["player_id"] == pid].sort_values("date")
p_well  = wellness[wellness["player_id"] == pid].sort_values("date")

st.title("⚕️ Injury & Load Monitor")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(
    ["🚦 Squad Dashboard", "📈 ACWR & PMC", "📊 Monotony & Strain", "🤖 ML Risk Prediction"])

# ═══════════════════════════════════════════════════════════════════════════════
# SQUAD DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("Squad Injury Risk Overview", icon="🚦",
                   help_text=(
                       "Every player is classified into a risk zone based on their current ACWR "
                       "(Acute:Chronic Workload Ratio - how much they have done this week vs their average over the past month).<br><br>"
                       "<b>Optimal (0.8-1.3)</b> - safe to play full minutes.<br>"
                       "<b>Caution (1.3-1.5)</b> - recent load spike. Consider reduced minutes or extra recovery.<br>"
                       "<b>High Risk (&gt;1.5)</b> - substantially elevated injury risk. Rest recommended.<br>"
                       "<b>Under-training (&lt;0.8)</b> - insufficient recent load. Player may not be match-sharp.<br><br>"
                       "<b>Availability</b> - % of sessions attended. Low availability may indicate persistent niggles."
                   ))

    max_sessions = training.groupby("player_id").size().max()

    squad_rows = []
    for _, player in players.iterrows():
        p = training[training["player_id"] == player["id"]]
        if p.empty: continue
        acwr_df = calculate_acwr(p["srpe"], p["date"], acute_d, chronic_d)
        latest  = acwr_df.iloc[-1]
        avail   = availability_pct(training, int(player["id"]), max_sessions)

        w = wellness[wellness["player_id"] == player["id"]]
        wcomp = float(w["wellness_composite"].iloc[-1]) if not w.empty else 6.5

        squad_rows.append({
            "Player":      player["name"],
            "Position":    player["position"],
            "Age":         player["age"],
            "ACWR":        round(float(latest["acwr"]), 2),
            "Risk Zone":   acwr_zone(float(latest["acwr"])),
            "Acute Load":  round(float(latest["acute_load"]), 0),
            "Chronic Load":round(float(latest["chronic_load"]), 0),
            "Availability":avail,
            "Wellness":    round(wcomp, 1),
        })

    squad_df = pd.DataFrame(squad_rows).sort_values("ACWR", ascending=False)
    rc = squad_df["Risk Zone"].value_counts()

    kpi_row([
        kpi_card("High Risk",     int(rc.get("High Risk",      0)), accent=COLORS["danger"]),
        kpi_card("Caution",       int(rc.get("Caution",        0)), accent=COLORS["warning"]),
        kpi_card("Optimal",       int(rc.get("Optimal",        0)), accent=COLORS["success"]),
        kpi_card("Under-training",int(rc.get("Under-training", 0)), accent=COLORS["secondary"]),
        kpi_card("Avg Availability", f"{squad_df['Availability'].mean():.0f}%", accent=COLORS["primary"]),
        kpi_card("Avg Wellness",  f"{squad_df['Wellness'].mean():.1f}", accent=COLORS["primary"]),
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    def _style_row(row):
        c = {"High Risk": f"background:#3a0d0d;color:{COLORS['danger']}",
             "Caution":   f"background:#3a2800;color:{COLORS['warning']}",
             "Optimal":   f"background:#0d2e1f;color:{COLORS['success']}",
             "Under-training": f"background:#1a1a36;color:{COLORS['secondary']}"}.get(row["Risk Zone"], "")
        return [c if col in ("Risk Zone", "ACWR") else "" for col in row.index]

    st.dataframe(squad_df.style.apply(_style_row, axis=1),
                 width="stretch", hide_index=True)

    # ACWR distribution
    zone_colors = [ACWR_ZONES[z][2] for z in squad_df["Risk Zone"]]
    fig = px.histogram(squad_df, x="ACWR", nbins=14, color="Risk Zone",
                       color_discrete_map={z: ACWR_ZONES[z][2] for z in ACWR_ZONES},
                       title="Squad ACWR Distribution")
    for x_val, label in [(0.8, "0.8"), (1.3, "1.3"), (1.5, "1.5")]:
        fig.add_vline(x=x_val, line_dash="dash", line_color=COLORS["muted"],
                      annotation_text=label, annotation_font_color=COLORS["muted"])
    fig = style_chart(fig, height=270)
    st.plotly_chart(fig, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# ACWR & PMC
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    if p_train.empty:
        st.warning("No training data for this player.")
    else:
        # ACWR
        acwr_df = calculate_acwr(p_train["srpe"], p_train["date"], acute_d, chronic_d)

        section_header(f"ACWR - {name}", icon="📈",
                       help_text=(
                           "<b>ACWR (Acute:Chronic Workload Ratio)</b> - divides last week's training load by the rolling monthly average.<br><br>"
                           "Formula: Acute load (recent {acute_d} days) / Chronic load (past {chronic_d} days)<br><br>"
                           "Load is measured in <b>sRPE</b> (Session Rating of Perceived Exertion) - session duration (minutes) x RPE score (1-10).<br><br>"
                           "The coloured zones are: blue = under-training, green = optimal, amber = caution, red = high risk. "
                           "The goal is to keep the ACWR line in the green zone as consistently as possible."
                       ).format(acute_d=acute_d, chronic_d=chronic_d))
        info_box(
            f"Acute ({acute_d}d) : Chronic ({chronic_d}d) ratio using sRPE load. "
            "Optimal zone: <b>0.8–1.3</b>. Above 1.5 = High Risk."
        )

        fig = go.Figure()
        fig.add_hrect(y0=0,    y1=0.8,  fillcolor=ACWR_ZONES["Under-training"][2], opacity=0.07, line_width=0)
        fig.add_hrect(y0=0.8,  y1=1.3,  fillcolor=ACWR_ZONES["Optimal"][2],        opacity=0.07, line_width=0)
        fig.add_hrect(y0=1.3,  y1=1.5,  fillcolor=ACWR_ZONES["Caution"][2],        opacity=0.10, line_width=0)
        fig.add_hrect(y0=1.5,  y1=3.0,  fillcolor=ACWR_ZONES["High Risk"][2],      opacity=0.10, line_width=0)

        fig.add_trace(go.Scatter(x=acwr_df["date"], y=acwr_df["acute_load"],
                                 name="Acute Load", yaxis="y2",
                                 line=dict(color=COLORS["primary"], width=1.5, dash="dot"), opacity=0.7))
        fig.add_trace(go.Scatter(x=acwr_df["date"], y=acwr_df["chronic_load"],
                                 name="Chronic Load", yaxis="y2",
                                 line=dict(color=COLORS["secondary"], width=1.5, dash="dash"), opacity=0.7))
        fig.add_trace(go.Scatter(x=acwr_df["date"], y=acwr_df["acwr"],
                                 name="ACWR", line=dict(color=COLORS["warning"], width=3)))

        fig = style_chart(fig, height=360,
                          yaxis=dict(title="ACWR", range=[0, 2.5], gridcolor=COLORS["grid"]),
                          yaxis2=dict(title="Load (sRPE AU)", overlaying="y", side="right", showgrid=False),
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch")

        # PMC
        pmc_df = calculate_pmc(p_train["srpe"], p_train["date"])
        section_header(f"Performance Management Chart (PMC) - {name}", icon="📉",
                       help_text=(
                           "The PMC tracks three interconnected load concepts over the season:<br><br>"
                           "<b>CTL - Chronic Training Load (Fitness)</b> - 42-day exponentially weighted average of daily load. "
                           "A rising CTL means the player is building fitness.<br><br>"
                           "<b>ATL - Acute Training Load (Fatigue)</b> - 7-day EWMA. Spikes when the player trains hard in a short period.<br><br>"
                           "<b>TSB - Training Stress Balance (Form)</b> = CTL minus ATL. "
                           "Positive TSB = rested and fresh. Negative TSB = fatigued but potentially fitter. "
                           "TSB of +5 to +25 before a big match is ideal."
                       ))
        info_box(
            "<b>CTL (Fitness)</b> = 42-day EWMA of daily load. "
            "<b>ATL (Fatigue)</b> = 7-day EWMA. "
            "<b>TSB (Form)</b> = CTL − ATL. "
            "TSB > +5 = Peaked · −10 to +5 = Optimal · < −30 = Overtraining risk."
        )

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=pmc_df["date"], y=pmc_df["ctl"],
                                  name="CTL (Fitness)", line=dict(color=COLORS["primary"], width=2.5)))
        fig2.add_trace(go.Scatter(x=pmc_df["date"], y=pmc_df["atl"],
                                  name="ATL (Fatigue)", line=dict(color=COLORS["danger"], width=2)))
        fig2.add_trace(go.Scatter(x=pmc_df["date"], y=pmc_df["tsb"],
                                  name="TSB (Form)", yaxis="y2",
                                  line=dict(color=COLORS["warning"], width=2, dash="dot")))
        fig2.add_hline(y=0, line_dash="dash", line_color=COLORS["muted"], line_width=1)
        fig2 = style_chart(fig2, height=340,
                           yaxis=dict(title="Load (AU)", gridcolor=COLORS["grid"]),
                           yaxis2=dict(title="TSB (Form)", overlaying="y", side="right",
                                       zeroline=True, zerolinecolor=COLORS["muted"], showgrid=False),
                           legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig2, width="stretch")

        # Load calendar heatmap
        acwr_df["week"] = acwr_df["date"].dt.isocalendar().week
        acwr_df["dow"]  = acwr_df["date"].dt.day_name()
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        acwr_df["dow"] = pd.Categorical(acwr_df["dow"], categories=dow_order, ordered=True)
        pivot = (acwr_df.pivot_table(index="week", columns="dow", values="daily_load",
                                     aggfunc="sum", observed=False)
                 .reindex(columns=dow_order))
        fig3 = px.imshow(pivot, color_continuous_scale="YlOrRd",
                         labels=dict(x="Day", y="Week", color="Load"),
                         title="Training Load Calendar Heatmap (sRPE)")
        fig3 = style_chart(fig3, height=300)
        st.plotly_chart(fig3, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# MONOTONY & STRAIN
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    if p_train.empty:
        st.warning("No training data.")
    else:
        ms_df = calculate_monotony_strain(p_train["srpe"], p_train["date"])
        ms_clean = ms_df.dropna(subset=["monotony"])

        section_header(f"Monotony & Strain - {name}", icon="📊",
                       help_text=(
                           "<b>Monotony</b> (Foster, 1998) measures how repetitive the training load is. "
                           "Calculated as: rolling mean load / rolling standard deviation.<br><br>"
                           "A value above 2.0 means the player is doing very similar load day-to-day - "
                           "little variation in training stimulus, associated with higher injury and burnout risk.<br><br>"
                           "<b>Strain</b> = weekly total load x monotony. It combines volume and repetitiveness into one figure. "
                           "High strain means lots of load AND that load is monotonous - the worst combination.<br><br>"
                           "The fix is varied session types: mix high-intensity with recovery sessions."
                       ))
        info_box(
            "<b>Monotony</b> (Foster 1998) = rolling mean / rolling std. "
            "Values above 2.0 indicate repetitive training patterns associated with increased injury risk. "
            "<b>Strain</b> = mean × monotony - captures combined volume and repetitiveness."
        )

        l, r = st.columns(2)
        with l:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ms_clean["date"], y=ms_clean["monotony"],
                                     fill="tozeroy", fillcolor=f"rgba(245,158,11,0.15)",
                                     line=dict(color=COLORS["warning"], width=2), name="Monotony"))
            fig.add_hline(y=2.0, line_dash="dash", line_color=COLORS["danger"],
                          annotation_text="Risk threshold (2.0)")
            fig = style_chart(fig, height=260, yaxis=dict(title="Monotony", gridcolor=COLORS["grid"]))
            fig.update_layout(title="Training Monotony (7-day)")
            st.plotly_chart(fig, width="stretch")
        with r:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=ms_clean["date"], y=ms_clean["strain"],
                                      fill="tozeroy", fillcolor=f"rgba(239,68,68,0.15)",
                                      line=dict(color=COLORS["danger"], width=2), name="Strain"))
            fig2 = style_chart(fig2, height=260, yaxis=dict(title="Strain", gridcolor=COLORS["grid"]))
            fig2.update_layout(title="Training Strain (7-day)")
            st.plotly_chart(fig2, width="stretch")

        # Session type breakdown
        stype_load = (p_train.groupby("session_type")
                      .agg(avg_srpe=("srpe", "mean"), sessions=("srpe", "count"))
                      .reset_index().sort_values("avg_srpe", ascending=True))
        fig3 = go.Figure(go.Bar(
            x=stype_load["avg_srpe"], y=stype_load["session_type"],
            orientation="h", marker_color=PALETTE[:len(stype_load)],
            text=stype_load["avg_srpe"].round(0).astype(int), textposition="outside",
        ))
        fig3 = style_chart(fig3, height=240,
                           xaxis=dict(title="Avg sRPE Load", gridcolor=COLORS["grid"]))
        fig3.update_layout(title="Average Load by Session Type")
        st.plotly_chart(fig3, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# ML RISK PREDICTION
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    section_header("ML Injury Risk Prediction", icon="🤖",
                   help_text=(
                       "A <b>Random Forest classifier</b> trained on the squad's training and wellness data. "
                       "It predicts the probability that a player is currently at elevated injury risk.<br><br>"
                       "<b>Input features used:</b> ACWR, age, training monotony, strain, days since last rest day, "
                       "wellness composite score, and 7-day sRPE total.<br><br>"
                       "<b>Output</b> - a risk probability (0-100%) per player. "
                       "This is a supplementary signal - it should be read alongside the ACWR chart, not instead of it.<br><br>"
                       "Important: the model is trained on synthetic data for this assignment. "
                       "In a real deployment it would be retrained on historical injury records."
                   ))
    info_box(
        "A <b>Random Forest classifier</b> (150 trees) trained on synthetic injury data. "
        "Input features: ACWR, age, training monotony, strain, days since rest, "
        "wellness composite, 7-day sRPE. "
        "Output: probability (0–100%) of current elevated injury risk."
    )

    with st.spinner("Running model predictions…"):
        acwr_map  = {int(p["id"]): calculate_acwr(training[training["player_id"]==p["id"]]["srpe"],
                                                   training[training["player_id"]==p["id"]]["date"])
                     for _, p in players.iterrows()}
        mono_map  = {int(p["id"]): calculate_monotony_strain(training[training["player_id"]==p["id"]]["srpe"],
                                                              training[training["player_id"]==p["id"]]["date"])
                     for _, p in players.iterrows()}
        risk_df, model_metrics = predict_squad_risk(players, training, wellness, acwr_map, mono_map)

    # Gauge for selected player
    sel_row = risk_df[risk_df["player_name"] == name]
    if not sel_row.empty:
        rv = float(sel_row["risk_pct"].values[0])
        g_color = COLORS["danger"] if rv > 60 else COLORS["warning"] if rv > 35 else COLORS["success"]
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rv,
            number={"suffix": "%", "font": {"color": g_color, "size": 40}},
            title={"text": f"{name} - Predicted Injury Risk", "font": {"color": COLORS["text"]}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": COLORS["muted"]},
                "bar":  {"color": g_color},
                "steps": [
                    {"range": [0,  25], "color": "#0d3324"},
                    {"range": [25, 50], "color": "#1a3a20"},
                    {"range": [50, 75], "color": "#3a2800"},
                    {"range": [75, 100],"color": "#3a0d0d"},
                ],
                "threshold": {"line": {"color": COLORS["danger"], "width": 3}, "value": 60},
            },
        ))
        fig_g.update_layout(paper_bgcolor=COLORS["bg"], font=dict(color=COLORS["muted"]),
                            height=300, margin=dict(t=50, b=20))
        st.plotly_chart(fig_g, width="stretch")

    # Squad risk bar
    top15 = risk_df.head(15)
    bar_col = [COLORS["danger"] if r > 60 else COLORS["warning"] if r > 35 else COLORS["success"]
               for r in top15["risk_pct"]]
    fig2 = go.Figure(go.Bar(
        x=top15["risk_pct"], y=top15["player_name"],
        orientation="h", marker_color=bar_col,
        text=[f"{r:.0f}%" for r in top15["risk_pct"]], textposition="outside",
    ))
    fig2.add_vline(x=60, line_dash="dash", line_color=COLORS["danger"],
                   annotation_text="High 60%", annotation_font_color=COLORS["danger"])
    fig2.add_vline(x=35, line_dash="dash", line_color=COLORS["warning"],
                   annotation_text="Moderate 35%", annotation_font_color=COLORS["warning"])
    fig2 = style_chart(fig2, height=440,
                       xaxis=dict(range=[0, 110], title="Risk %", gridcolor=COLORS["grid"]),
                       yaxis=dict(autorange="reversed"))
    fig2.update_layout(title="Top 15 - Predicted Injury Risk", margin=dict(l=150))
    st.plotly_chart(fig2, width="stretch")

    # Feature importances - from the fitted model, not hardcoded
    fi = model_metrics["feature_importances"].sort_values("Importance")
    fig3 = go.Figure(go.Bar(
        x=fi["Importance"], y=fi["Feature"],
        orientation="h", marker_color=PALETTE[:len(fi)],
        text=[f"{v:.0%}" for v in fi["Importance"]], textposition="outside",
    ))
    fig3 = style_chart(fig3, height=260,
                       xaxis=dict(title="Relative Importance", gridcolor=COLORS["grid"]))
    fig3.update_layout(title="Random Forest Feature Importances (fitted model)")
    st.plotly_chart(fig3, width="stretch")

    # Model validation metrics
    st.markdown("**Model validation (held-out 30% test set)**")
    cols = st.columns(5)
    cols[0].metric("AUC-ROC",   f"{model_metrics['test_auc']:.3f}")
    cols[1].metric("Precision", f"{model_metrics['test_precision']:.3f}")
    cols[2].metric("Recall",    f"{model_metrics['test_recall']:.3f}")
    cols[3].metric("F1",        f"{model_metrics['test_f1']:.3f}")
    cols[4].metric("CV AUC",    f"{model_metrics['cv_auc_mean']:.3f} ±{model_metrics['cv_auc_std']:.3f}")
    st.caption(
        f"Trained on {model_metrics['n_train']:,} synthetic samples · "
        f"tested on {model_metrics['n_test']:,} held-out samples · "
        "⚠️ Metrics reflect recovery of the synthetic generating function, "
        "not real-world predictive validity."
    )
