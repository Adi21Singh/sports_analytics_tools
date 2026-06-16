"""
pages/press_intelligence.py
============================
Press Intelligence — windowed PPDA analysis with Opponent Build-up Tendency
classification, Second-Ball Recovery, Context Layer, and Match Momentum Index.

Data source: StatsBomb open data, La Liga 2015/16 (competition_id=11).

Key design choice — why the Build-up Tendency classifier exists
---------------------------------------------------------------
Standard PPDA computes opponent_passes_in_zone / our_defensive_actions.  When
an opponent sits deep or plays direct, their zone-pass count is near zero by
design, not because our press forced it.  This module detects such windows and
(a) strips the misleading teal colouring from the Press Timeline, (b) surfaces
second-ball recovery rate as the headline metric instead, and (c) down-weights
those windows in the Match Momentum Index.
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, info_box
from config import COLORS

from analytics.press_engine import (
    load_sb_matches,
    compute_ppda_windows,
    run_threshold_validator,
    classify_buildup_tendency,
    SB_AVAILABLE,
    LA_LIGA_COMPETITION_ID,
    PPDA_COLLAPSE_THRESHOLD,
    MIN_EVENTS_GREY_OUT,
    BUILDUP_MIN_ZONE_PASSES,
    DIRECT_LONG_PASS_RATIO_THRESHOLD,
    MIXED_LONG_PASS_RATIO_LOWER,
    LONG_PASS_LENGTH_METRES,
    SECOND_BALL_RECOVERY_SECONDS,
    DIRECT_PPDA_WEIGHT_FACTOR,
    CATEGORY_BUILDUP,
    CATEGORY_MIXED,
    CATEGORY_DIRECT,
)

styles.apply()

# ── Colour palette for this module ────────────────────────────────────────────
_TEAL         = COLORS["primary"]
_AMBER        = COLORS["warning"]
_GREY         = COLORS["muted"]
_MUTED        = "#6b7280"
_DIRECT_HATCH = "/"

# ── StatsBomb availability check ─────────────────────────────────────────────
if not SB_AVAILABLE:
    st.error(
        "**statsbombpy is not installed.**  "
        "Run `pip install statsbombpy` and restart the app."
    )
    st.stop()

# ── Cached loaders ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading La Liga 2015/16 matches…")
def _cached_matches() -> pd.DataFrame:
    return load_sb_matches()


@st.cache_data(show_spinner="Computing press windows…")
def _cached_windows(match_id: int, our_team: str, opponent_team: str):
    return compute_ppda_windows(match_id, our_team, opponent_team)


@st.cache_data(show_spinner="Running threshold validator (first run can take a while)…")
def _cached_validator():
    return run_threshold_validator()


# ── Load La Liga 2015/16 matches ──────────────────────────────────────────────
try:
    matches_df = _cached_matches()
except Exception as e:
    st.error(f"Could not load La Liga 2015/16 matches: {e}")
    st.stop()

if matches_df.empty:
    st.warning("No matches found for La Liga 2015/16.")
    st.stop()

# ── Team name extraction ───────────────────────────────────────────────────────
def _tn(val) -> str:
    if isinstance(val, dict):
        for k in ("home_team_name", "away_team_name", "name"):
            if k in val:
                return val[k]
    return str(val) if pd.notna(val) else ""

matches_df["_home"] = matches_df.get(
    "home_team", pd.Series("", index=matches_df.index)
).apply(_tn)
matches_df["_away"] = matches_df.get(
    "away_team", pd.Series("", index=matches_df.index)
).apply(_tn)

def _match_label(row) -> str:
    date = str(row.get("match_date", row.get("match_week", "")))
    return f"{row['_home']} vs {row['_away']}  [{date}]"

matches_df["_label"] = matches_df.apply(_match_label, axis=1)

with st.sidebar:
    st.markdown("### 🔍 Press Intelligence")
    st.caption("StatsBomb open data · La Liga 2015/16")
    selected_label = st.selectbox("Select Match", matches_df["_label"].tolist(), key="pi_match")
    sel_row = matches_df[matches_df["_label"] == selected_label].iloc[0]
    home_team = sel_row["_home"]
    away_team = sel_row["_away"]
    match_id  = int(sel_row["match_id"])

    our_team = st.radio("Analyse press for:", [home_team, away_team])
    opponent_team = away_team if our_team == home_team else home_team

# ── Page title ────────────────────────────────────────────────────────────────
st.title("🔍 Press Intelligence")
_c_muted = COLORS["muted"]
_c_text  = COLORS["text"]
st.markdown(
    f"<span style='font-size:1.1rem;color:{_c_muted};'>"
    f"{home_team} vs {away_team} &nbsp;·&nbsp; "
    f"Analysing: <b style='color:{_c_text};'>{our_team}</b>"
    f"</span>",
    unsafe_allow_html=True,
)
st.divider()

# ── Compute windows ───────────────────────────────────────────────────────────
try:
    win_df = _cached_windows(match_id, our_team, opponent_team)
except Exception as e:
    st.error(f"Could not compute press windows: {e}")
    st.stop()

if win_df.empty:
    st.warning("No window data available for this match.")
    st.stop()

# ── Summary KPIs ─────────────────────────────────────────────────────────────
valid_wins  = win_df[win_df["sufficient_data"]]
direct_wins = win_df[win_df["build_up_tendency"] == CATEGORY_DIRECT]
buildup_wins = win_df[win_df["build_up_tendency"] == CATEGORY_BUILDUP]

avg_ppda_buildup = (
    valid_wins[valid_wins["build_up_tendency"] != CATEGORY_DIRECT]["ppda"]
    .dropna().mean()
)
avg_mom    = win_df["momentum_index"].dropna().mean()
n_direct   = len(direct_wins)
n_total    = len(win_df)
direct_pct = n_direct / max(n_total, 1)
avg_sb_rate = direct_wins["second_ball_recovery_rate"].mean() if not direct_wins.empty else 0.0
avg_psr     = valid_wins["pressing_success_rate"].mean() if not valid_wins.empty else 0.0

kpi_row([
    kpi_card(
        "Avg PPDA (Build-up windows)",
        f"{avg_ppda_buildup:.1f}" if not np.isnan(avg_ppda_buildup) else "—",
        sub="excl. Direct/Defensive", accent=COLORS["primary"]
    ),
    kpi_card(
        "Direct/Defensive Windows",
        f"{n_direct}/{n_total}",
        sub=f"{direct_pct:.0%} of match", accent=COLORS["secondary"]
    ),
    kpi_card(
        "2nd-Ball Recovery Rate",
        f"{avg_sb_rate:.0%}" if not direct_wins.empty else "—",
        sub="Direct windows only", accent=COLORS["warning"]
    ),
    kpi_card(
        "Pressing Success Rate",
        f"{avg_psr:.0%}",
        sub="regains / pressures", accent=COLORS["success"]
    ),
    kpi_card(
        "Avg Momentum Index",
        f"{avg_mom:.0f}/100" if not np.isnan(avg_mom) else "—",
        sub="0=poor · 100=dominant", accent=COLORS["primary"]
    ),
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Strategy / interpretation text ───────────────────────────────────────────
if direct_pct > 0.5:
    st.info(
        f"**Opponent is playing direct:** {direct_pct:.0%} of windows are classified "
        f"\"Direct/Defensive\" — {opponent_team} rarely committed to building through "
        f"their defensive zone.  PPDA understates press difficulty in this match.  "
        f"**Second-ball recovery rate ({avg_sb_rate:.0%}) is the primary signal** — "
        f"press triggers on long-ball second balls are more effective than structured "
        f"build-up pressure.  Consider prioritising recovery positioning over high-line pressing."
    )
elif direct_pct > 0.25:
    st.warning(
        f"**Mixed build-up match:** {direct_pct:.0%} of windows show direct play.  "
        f"Monitor both PPDA (Build-up windows, avg {avg_ppda_buildup:.1f}) and "
        f"second-ball recovery rate ({avg_sb_rate:.0%}) as complementary signals."
    )
else:
    ppda_verdict = "effective" if not np.isnan(avg_ppda_buildup) and avg_ppda_buildup <= PPDA_COLLAPSE_THRESHOLD else "under pressure"
    st.success(
        f"**Genuine build-up match:** {opponent_team} mostly built through their "
        f"defensive zone.  PPDA is a reliable signal — press is **{ppda_verdict}** "
        f"(avg PPDA {avg_ppda_buildup:.1f}, threshold {PPDA_COLLAPSE_THRESHOLD})."
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_timeline, tab_context, tab_momentum, tab_validator = st.tabs([
    "📊 Press Timeline",
    "🗂 Context Layer",
    "📈 Momentum Index",
    "✅ Threshold Validator",
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRESS TIMELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    section_header("PPDA Press Timeline", icon="📊",
                   subtitle="10-minute windows  ·  teal = good press  ·  amber = collapsing  ·  hatched = Direct/Defensive (PPDA unreliable)")

    info_box(
        "When a window is classified <b>Direct/Defensive</b> (hatched bars), the opponent "
        "rarely attempted passes in their defensive zone.  PPDA is not a reliable press "
        "signal for those windows — the headline metric switches to "
        "<b>second-ball recovery rate</b> instead."
    )

    labels     = win_df["window_label"].tolist()
    n_windows  = len(labels)

    # Build per-category y arrays (None = bar not rendered for this window)
    y_good    = []   # teal
    y_poor    = []   # amber
    y_insuff  = []   # grey stub
    y_direct  = []   # hatched

    for _, row in win_df.iterrows():
        ppda  = row["ppda"]
        suff  = row["sufficient_data"]
        tend  = row["build_up_tendency"]

        is_null = ppda is None or (isinstance(ppda, float) and np.isnan(ppda))

        if not suff or is_null:
            y_good.append(None);  y_poor.append(None)
            y_insuff.append(MIN_EVENTS_GREY_OUT * 0.5)   # show a stub
            y_direct.append(None)
        elif tend == CATEGORY_DIRECT:
            y_good.append(None);  y_poor.append(None);  y_insuff.append(None)
            y_direct.append(float(ppda))
        elif float(ppda) <= PPDA_COLLAPSE_THRESHOLD:
            y_good.append(float(ppda));  y_poor.append(None)
            y_insuff.append(None);       y_direct.append(None)
        else:
            y_good.append(None);  y_poor.append(float(ppda))
            y_insuff.append(None);  y_direct.append(None)

    # Build hover texts
    def _hover(row):
        ppda = row["ppda"]
        tend = row["build_up_tendency"]
        suff = row["sufficient_data"]
        is_null = ppda is None or (isinstance(ppda, float) and np.isnan(ppda))

        h = f"<b>{row['window_label']}</b><br>"
        if not suff or is_null:
            h += f"Insufficient data (< {MIN_EVENTS_GREY_OUT} combined events)"
        elif tend == CATEGORY_DIRECT:
            h += (
                f"PPDA: {ppda:.1f} — <i>not a reliable signal this window</i><br>"
                f"Opponent played direct — PPDA not a reliable press signal this window.<br>"
                f"Zone passes: {row['opp_zone_passes']}  ·  "
                f"Long-pass ratio: {row['long_pass_ratio']:.0%}<br>"
                f"<b>2nd-ball recovery rate: {row['second_ball_recovery_rate']:.0%}</b> "
                f"({row['second_ball_recoveries']} recoveries)"
            )
        else:
            emoji = "✓" if ppda <= PPDA_COLLAPSE_THRESHOLD else "⚠"
            h += (
                f"PPDA: {ppda:.1f} {emoji}<br>"
                f"Zone passes: {row['opp_zone_passes']}  ·  "
                f"Our actions: {row['our_defensive_actions']}<br>"
                f"Build-up tendency: {tend}<br>"
                f"Pressing success: {row['pressing_success_rate']:.0%}"
            )
        return h

    hover_texts = win_df.apply(_hover, axis=1).tolist()

    fig = go.Figure()

    # Common bar kwargs
    _bar_kw = dict(x=labels, showlegend=True)

    fig.add_trace(go.Bar(
        **_bar_kw, name="Good press",
        y=y_good,
        marker=dict(color=_TEAL, opacity=0.9),
        hovertext=[h if y is not None else "" for h, y in zip(hover_texts, y_good)],
        hoverinfo="text",
    ))
    fig.add_trace(go.Bar(
        **_bar_kw, name="Press collapsing",
        y=y_poor,
        marker=dict(color=_AMBER, opacity=0.9),
        hovertext=[h if y is not None else "" for h, y in zip(hover_texts, y_poor)],
        hoverinfo="text",
    ))
    fig.add_trace(go.Bar(
        **_bar_kw, name="Direct/Defensive (PPDA unreliable)",
        y=y_direct,
        marker=dict(
            color=_MUTED,
            opacity=0.7,
            pattern=dict(shape=_DIRECT_HATCH, fgcolor="rgba(255,255,255,0.45)", size=6),
        ),
        hovertext=[h if y is not None else "" for h, y in zip(hover_texts, y_direct)],
        hoverinfo="text",
    ))
    fig.add_trace(go.Bar(
        **_bar_kw, name="Insufficient data",
        y=y_insuff,
        marker=dict(color=_GREY, opacity=0.4),
        hovertext=[h if y is not None else "" for h, y in zip(hover_texts, y_insuff)],
        hoverinfo="text",
    ))

    fig.add_hline(
        y=PPDA_COLLAPSE_THRESHOLD,
        line_dash="dash", line_color=COLORS["danger"],
        annotation_text=f"Collapse threshold ({PPDA_COLLAPSE_THRESHOLD})",
        annotation_font_color=COLORS["danger"],
    )

    fig = style_chart(
        fig, height=380,
        xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
        yaxis=dict(title="PPDA  (lower = better press)", gridcolor=COLORS["grid"]),
    )
    fig.update_layout(barmode="overlay")
    st.plotly_chart(fig, width='stretch')

    # ── Direct/Defensive window detail table ──────────────────────────────
    if not direct_wins.empty:
        st.markdown("#### Direct/Defensive Windows — Alternative Metric")
        st.caption(
            "For these windows, second-ball recovery rate is the headline signal "
            "instead of PPDA."
        )
        detail_cols = [
            "window_label", "opp_zone_passes", "long_pass_ratio",
            "second_ball_recovery_rate", "second_ball_recoveries",
        ]
        detail = direct_wins[detail_cols].copy()
        detail.columns = [
            "Window", "Opp Zone Passes", "Long-Pass Ratio",
            "2nd-Ball Recovery Rate", "Recoveries",
        ]
        detail["Long-Pass Ratio"] = detail["Long-Pass Ratio"].map("{:.0%}".format)
        detail["2nd-Ball Recovery Rate"] = detail["2nd-Ball Recovery Rate"].map("{:.0%}".format)
        st.dataframe(detail, width='stretch', hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONTEXT LAYER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_context:
    section_header("Context Layer", icon="🗂",
                   subtitle="Possession · Pressing Success · Defensive Territory Depth")

    c1, c2 = st.columns(2)

    with c1:
        # Possession by window
        section_header("Possession by Period", icon="🔵")
        fig_poss = go.Figure()
        fig_poss.add_trace(go.Bar(
            x=labels, y=win_df["our_poss_share"] * 100,
            name=our_team, marker_color=_TEAL, opacity=0.85,
        ))
        fig_poss.add_trace(go.Bar(
            x=labels, y=win_df["opp_poss_share"] * 100,
            name=opponent_team, marker_color=_AMBER, opacity=0.65,
        ))
        fig_poss.add_hline(y=50, line_dash="dot", line_color=_GREY)
        fig_poss = style_chart(
            fig_poss, height=280, barmode="group",
            yaxis=dict(title="Possession %", range=[0, 100], gridcolor=COLORS["grid"]),
            xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
        )
        st.plotly_chart(fig_poss, width='stretch')

        # Pressing success rate
        section_header("Pressing Success Rate", icon="🎯")
        psr_colors = [
            _TEAL if r >= 0.30 else _AMBER if r >= 0.15 else _GREY
            for r in win_df["pressing_success_rate"]
        ]
        fig_psr = go.Figure(go.Bar(
            x=labels, y=win_df["pressing_success_rate"] * 100,
            marker_color=psr_colors, opacity=0.9,
            hovertemplate="%{x}<br>Pressing success: %{y:.1f}%<extra></extra>",
        ))
        fig_psr.add_hline(y=30, line_dash="dash", line_color=_TEAL,
                          annotation_text="30% good", annotation_font_color=_TEAL)
        fig_psr = style_chart(
            fig_psr, height=250,
            yaxis=dict(title="Success Rate %", gridcolor=COLORS["grid"]),
            xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
        )
        st.plotly_chart(fig_psr, width='stretch')

    with c2:
        # Defensive territory depth
        section_header("Defensive Territory Depth", icon="🛡️")
        info_box(
            "Higher = our defensive actions occur further up the pitch = deeper press.  "
            "Midfield ≈ 60 m.  Opponent's box ≈ 100 m."
        )
        depth_colors = [
            _TEAL if d >= 70 else _AMBER if d >= 50 else COLORS["danger"]
            for d in win_df["territory_depth"]
        ]
        fig_depth = go.Figure(go.Bar(
            x=labels, y=win_df["territory_depth"],
            marker_color=depth_colors, opacity=0.85,
            hovertemplate="%{x}<br>Territory depth: %{y:.0f} m<extra></extra>",
        ))
        fig_depth.add_hline(y=60, line_dash="dot", line_color=_GREY,
                             annotation_text="Midfield")
        fig_depth.add_hline(y=80, line_dash="dash", line_color=_TEAL,
                             annotation_text="High press zone")
        fig_depth = style_chart(
            fig_depth, height=280,
            yaxis=dict(title="Avg x of defensive actions (m)",
                       range=[0, 120], gridcolor=COLORS["grid"]),
            xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
        )
        st.plotly_chart(fig_depth, width='stretch')

        # Second-ball recovery breakdown (all windows)
        section_header("2nd-Ball Recovery by Third", icon="⚽")
        thirds_data = {"Defensive": 0, "Middle": 0, "Attacking": 0}
        for _, row in win_df.iterrows():
            thirds = row.get("recovery_thirds", {})
            if isinstance(thirds, dict):
                for k in thirds_data:
                    thirds_data[k] += thirds.get(k, 0)

        fig_thirds = go.Figure(go.Pie(
            labels=list(thirds_data.keys()),
            values=list(thirds_data.values()),
            marker=dict(colors=[COLORS["danger"], COLORS["warning"], _TEAL]),
            hole=0.5, textinfo="label+percent",
        ))
        fig_thirds = style_chart(fig_thirds, height=250)
        fig_thirds.update_traces(textfont_color=COLORS["text"])
        st.plotly_chart(fig_thirds, width='stretch')


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — MOMENTUM INDEX
# ═══════════════════════════════════════════════════════════════════════════════
with tab_momentum:
    section_header("Match Momentum Index", icon="📈",
                   subtitle=f"Combining PPDA trend ({int(100*0.60)}% weight) + Territory Depth ({int(100*0.40)}% weight)")

    info_box(
        f"<b>Direct/Defensive windows</b> have their PPDA component down-weighted by "
        f"{int(DIRECT_PPDA_WEIGHT_FACTOR * 100)}× (from 60% to "
        f"{DIRECT_PPDA_WEIGHT_FACTOR * 60:.0f}% of the index) to prevent an artefactually low "
        f"PPDA from inflating the momentum score.  Grey markers = insufficient data."
    )

    mom_vals = win_df["momentum_index"].tolist()
    tend_list = win_df["build_up_tendency"].tolist()
    suff_list = win_df["sufficient_data"].tolist()

    # Line for the index
    fig_mom = go.Figure()

    # Colour the line points by tendency
    for i, (label, mom, tend, suff) in enumerate(
        zip(labels, mom_vals, tend_list, suff_list)
    ):
        if mom is None or (isinstance(mom, float) and np.isnan(mom)):
            continue
        if not suff:
            color = _GREY
        elif tend == CATEGORY_DIRECT:
            color = _MUTED
        elif float(mom) >= 60:
            color = _TEAL
        else:
            color = _AMBER

        fig_mom.add_trace(go.Scatter(
            x=[label], y=[mom],
            mode="markers",
            marker=dict(size=12, color=color,
                        symbol="circle" if tend != CATEGORY_DIRECT else "diamond",
                        line=dict(color=COLORS["bg"], width=1)),
            showlegend=False,
            hovertemplate=(
                f"<b>{label}</b><br>"
                f"Momentum: {mom:.0f}/100<br>"
                f"Tendency: {tend}<br>"
                f"{'⚠ PPDA down-weighted (Direct/Defensive)' if tend == CATEGORY_DIRECT else ''}"
                "<extra></extra>"
            ),
        ))

    # Connect with a line
    valid_mom = [
        (lbl, m) for lbl, m, s in zip(labels, mom_vals, suff_list)
        if s and m is not None and not (isinstance(m, float) and np.isnan(m))
    ]
    if valid_mom:
        x_line, y_line = zip(*valid_mom)
        fig_mom.add_trace(go.Scatter(
            x=list(x_line), y=list(y_line),
            mode="lines",
            line=dict(color=COLORS["primary"], width=2, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    fig_mom.add_hline(y=50, line_dash="dash", line_color=_GREY,
                      annotation_text="Neutral (50)", annotation_font_color=_GREY)
    fig_mom = style_chart(
        fig_mom, height=360,
        xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
        yaxis=dict(title="Momentum Index (0–100)", range=[0, 105],
                   gridcolor=COLORS["grid"]),
    )
    st.plotly_chart(fig_mom, width='stretch')

    # Legend explanation
    st.markdown(
        f"<small style='color:{_TEAL}'>●  Good press (Momentum ≥ 60)</small> &nbsp; "
        f"<small style='color:{_AMBER}'>●  Under pressure (Momentum < 60)</small> &nbsp; "
        f"<small style='color:{_MUTED}'>◆  Direct/Defensive (PPDA down-weighted)</small> &nbsp; "
        f"<small style='color:{_GREY}'>●  Insufficient data</small>",
        unsafe_allow_html=True,
    )

    # Window-by-window table
    st.markdown("<br>", unsafe_allow_html=True)
    mom_table = win_df[[
        "window_label", "build_up_tendency", "ppda",
        "territory_depth", "momentum_index", "sufficient_data",
    ]].copy()
    mom_table.columns = [
        "Window", "Build-up Tendency", "PPDA", "Territory Depth (m)",
        "Momentum Index", "Sufficient Data",
    ]
    mom_table["PPDA"] = mom_table["PPDA"].apply(
        lambda v: f"{v:.1f}" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "—"
    )
    mom_table["Momentum Index"] = mom_table["Momentum Index"].apply(
        lambda v: f"{v:.0f}" if v is not None else "—"
    )
    st.dataframe(mom_table, width='stretch', hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — THRESHOLD VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_validator:
    section_header("Threshold Validator", icon="✅",
                   subtitle="Backtested against La Liga 2015/16 (up to 380 matches)")

    info_box(
        "This validator runs the PPDA engine and Build-up Tendency Classifier across "
        "all available La Liga 2015/16 matches and reports the distribution of window "
        "categories.  The category distribution provides a data-driven justification "
        "for excluding or down-weighting Direct/Defensive windows in PPDA scoring."
    )

    run_col, _ = st.columns([1, 2])
    with run_col:
        run_validator = st.button("Run / Refresh Threshold Validator", type="primary")

    if run_validator or "validator_results" in st.session_state:
        if run_validator:
            with st.spinner("Running validator across all La Liga 2015/16 matches…"):
                results = _cached_validator()
            st.session_state["validator_results"] = results
        else:
            results = st.session_state["validator_results"]

        if "error" in results:
            st.error(results["error"])
        else:
            st.markdown("### Summary")
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Matches processed", results.get("n_matches", "—"))
            v2.metric("Total windows", results.get("n_windows_total", "—"))
            v3.metric("Valid windows", results.get("n_windows_valid", "—"))
            v4.metric("Collapse threshold", f"PPDA = {results.get('collapse_threshold', PPDA_COLLAPSE_THRESHOLD)}")

            st.markdown("### PPDA Distribution (Build-up + Mixed windows only)")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Mean PPDA",   results.get("ppda_mean",  "—"))
            p2.metric("Std Dev",     results.get("ppda_std",   "—"))
            p3.metric("25th pctile", results.get("ppda_p25",  "—"))
            p4.metric("75th pctile", results.get("ppda_p75",  "—"))

            # ── Category distribution — the new required line ──────────────
            st.markdown("### Build-up Category Distribution (all valid windows)")
            cat_dist = results.get("category_distribution", {})

            if cat_dist:
                cat_rows = []
                for cat in [CATEGORY_BUILDUP, CATEGORY_MIXED, CATEGORY_DIRECT]:
                    info = cat_dist.get(cat, {"count": 0, "fraction": 0.0})
                    cat_rows.append({
                        "Category":   cat,
                        "Windows":    info["count"],
                        "Fraction":   f"{info['fraction']:.1%}",
                        "Note": (
                            "Normal PPDA scoring applies"
                            if cat in (CATEGORY_BUILDUP, CATEGORY_MIXED)
                            else "PPDA down-weighted; 2nd-ball recovery used instead"
                        ),
                    })
                st.dataframe(pd.DataFrame(cat_rows), width='stretch', hide_index=True)

                # Quick bar chart
                frac_vals = [
                    cat_dist.get(c, {}).get("fraction", 0) * 100
                    for c in [CATEGORY_BUILDUP, CATEGORY_MIXED, CATEGORY_DIRECT]
                ]
                fig_cat = go.Figure(go.Bar(
                    x=[CATEGORY_BUILDUP, CATEGORY_MIXED, CATEGORY_DIRECT],
                    y=frac_vals,
                    marker_color=[_TEAL, _AMBER, _MUTED],
                    text=[f"{v:.1f}%" for v in frac_vals],
                    textposition="outside",
                ))
                fig_cat = style_chart(
                    fig_cat, height=260,
                    yaxis=dict(title="% of valid windows", range=[0, 100],
                               gridcolor=COLORS["grid"]),
                )
                fig_cat.update_layout(title="Window Category Distribution — La Liga 2015/16")
                st.plotly_chart(fig_cat, width='stretch')

                direct_frac = cat_dist.get(CATEGORY_DIRECT, {}).get("fraction", 0)
                st.success(
                    f"**Documentation note:** {direct_frac:.1%} of analysed windows "
                    f"were classified Direct/Defensive and excluded from PPDA-based "
                    f"momentum scoring.  These windows used second-ball recovery rate "
                    f"as the primary press signal instead."
                )
    else:
        st.info(
            "Click **Run / Refresh Threshold Validator** to backtest across all "
            "La Liga 2015/16 matches.  Results are cached after the first run."
        )
