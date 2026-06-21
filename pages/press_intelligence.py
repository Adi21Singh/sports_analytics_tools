"""
pages/press_intelligence.py
============================
Press Intelligence — full module:
  • Configurable PPDA threshold slider
  • Our press timeline + opponent press side-by-side
  • Goal / red-card annotations on the timeline
  • Context Layer (possession, success rate, territory depth)
  • Match Momentum Index
  • Substitution Pressing Profiles
  • Opponent Season Press History
  • Threshold Validator (backtested across 380 matches)
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from bisect import bisect_left, bisect_right
from collections import defaultdict

import ui.styles as styles
from ui.components import (
    kpi_card, kpi_row, section_header, style_chart,
    info_box, info_popover,
)
from config import COLORS

from analytics.press_engine import (
    load_sb_matches,
    load_match_events,
    compute_ppda_windows,
    run_threshold_validator,
    SB_AVAILABLE,
    CACHE_DIR,
    PPDA_COLLAPSE_THRESHOLD,
    MIN_EVENTS_GREY_OUT,
    CATEGORY_BUILDUP,
    CATEGORY_MIXED,
    CATEGORY_DIRECT,
    DIRECT_PPDA_WEIGHT_FACTOR,
)

styles.apply()

_TEAL  = COLORS["primary"]
_AMBER = COLORS["warning"]
_GREY  = COLORS["muted"]
_MUTED = "#6b7280"

if not SB_AVAILABLE:
    st.error("**statsbombpy is not installed.** Run `pip install statsbombpy` and restart.")
    st.stop()


# ── Cached loaders ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Loading La Liga 2015/16 matches…")
def _cached_matches() -> pd.DataFrame:
    return load_sb_matches()


@st.cache_data(show_spinner="Computing press windows…")
def _cached_windows(match_id: int, our_team: str, opponent_team: str) -> pd.DataFrame:
    return compute_ppda_windows(match_id, our_team, opponent_team)


@st.cache_data(show_spinner="Loading match events…")
def _cached_events(match_id: int) -> pd.DataFrame:
    return load_match_events(match_id)


@st.cache_data(show_spinner="Running threshold validator…")
def _cached_validator() -> dict:
    return run_threshold_validator()


@st.cache_data(show_spinner="Building pressing profiles from cached matches…")
def _build_pressing_profiles() -> pd.DataFrame:
    """Aggregate per-player pressing stats from all locally cached event files."""
    cached_ids = []
    for f in os.listdir(CACHE_DIR):
        if f.startswith("events_") and f.endswith(".csv"):
            try:
                cached_ids.append(int(f.replace("events_", "").replace(".csv", "")))
            except ValueError:
                pass

    all_rows = []
    for mid in cached_ids:
        try:
            ev = load_match_events(mid)
            if ev.empty or "type_name" not in ev.columns:
                continue

            max_min     = int(ev["minute"].max()) if "minute" in ev.columns else 90
            late_cutoff = max(0, max_min - 20)

            pev = ev[ev["type_name"] == "Pressure"].copy()
            if pev.empty or "player" not in pev.columns:
                continue
            pev["t_s"]     = pev["minute"] * 60 + pev["second"].fillna(0)
            pev["is_late"] = pev["minute"] >= late_cutoff

            regain_types = {"Interception", "Ball Recovery", "Tackle"}
            rev = ev[ev["type_name"].isin(regain_types)].copy()
            rev["t_s"] = rev["minute"] * 60 + rev["second"].fillna(0)

            team_rt: dict[str, list[float]] = defaultdict(list)
            for _, r in rev.iterrows():
                team_rt[str(r["team_name"])].append(float(r["t_s"]))
            for k in team_rt:
                team_rt[k].sort()

            regains = np.zeros(len(pev), dtype=bool)
            for i, (_, row) in enumerate(pev.iterrows()):
                t0    = float(row["t_s"])
                times = team_rt.get(str(row["team_name"]), [])
                if times:
                    lo = bisect_left(times, t0)
                    hi = bisect_right(times, t0 + 5.0)
                    regains[i] = lo < hi
            pev["is_regain"] = regains

            for (player, team), grp in pev.groupby(["player", "team_name"]):
                player = str(player)
                if player in ("nan", "None", ""):
                    continue
                all_rows.append({
                    "player":    player,
                    "team":      str(team),
                    "match_id":  mid,
                    "pressures": len(grp),
                    "regains":   int(grp["is_regain"].sum()),
                    "late":      int(grp["is_late"].sum()),
                })
        except Exception:
            continue

    if not all_rows:
        return pd.DataFrame()

    df  = pd.DataFrame(all_rows)
    agg = df.groupby(["player", "team"]).agg(
        matches       = ("match_id",  "nunique"),
        total_press   = ("pressures", "sum"),
        total_regains = ("regains",   "sum"),
        total_late    = ("late",      "sum"),
    ).reset_index()

    agg = agg[agg["matches"] >= 2]
    if agg.empty:
        return pd.DataFrame()

    agg["press_per_match"] = (agg["total_press"]   / agg["matches"]).round(1)
    agg["regain_rate"]     = (agg["total_regains"]  / agg["total_press"].clip(lower=1)).round(3)
    agg["late_per_match"]  = (agg["total_late"]     / agg["matches"]).round(1)
    return agg.sort_values("press_per_match", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner="Loading opponent press history…")
def _opponent_history(opponent: str) -> pd.DataFrame:
    """Season PPDA history for *opponent* as pressing team (cached matches only)."""
    def _tn(v):
        if isinstance(v, dict):
            return v.get("name", str(v))
        return str(v) if pd.notna(v) else ""

    cached_ids: set[int] = set()
    for f in os.listdir(CACHE_DIR):
        if f.startswith("events_") and f.endswith(".csv"):
            try:
                cached_ids.add(int(f.replace("events_", "").replace(".csv", "")))
            except ValueError:
                pass

    matches = load_sb_matches()
    matches["_home"] = matches.get("home_team", pd.Series("", index=matches.index)).apply(_tn)
    matches["_away"] = matches.get("away_team", pd.Series("", index=matches.index)).apply(_tn)

    opp_rows = matches[
        ((matches["_home"] == opponent) | (matches["_away"] == opponent)) &
        matches["match_id"].isin(list(cached_ids))
    ]

    rows = []
    for _, mrow in opp_rows.iterrows():
        mid  = int(mrow["match_id"])
        is_h = mrow["_home"] == opponent
        vs   = mrow["_away"] if is_h else mrow["_home"]
        date = str(mrow.get("match_date", ""))
        try:
            wdf   = compute_ppda_windows(mid, opponent, vs)
            if wdf.empty:
                continue
            valid = wdf[
                wdf["sufficient_data"] &
                (wdf["build_up_tendency"] != CATEGORY_DIRECT) &
                wdf["ppda"].notna()
            ]
            if valid.empty:
                continue
            rows.append({
                "Date":      date,
                "Opponent":  vs,
                "H/A":       "H" if is_h else "A",
                "Avg PPDA":  round(float(valid["ppda"].mean()), 2),
                "match_id":  mid,
            })
        except Exception:
            continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("Date").reset_index(drop=True)
    return df


# ── Load La Liga 2015/16 matches ──────────────────────────────────────────────
try:
    matches_df = _cached_matches()
except Exception as e:
    st.error(f"Could not load La Liga 2015/16 matches: {e}")
    st.stop()

if matches_df.empty:
    st.warning("No matches found for La Liga 2015/16.")
    st.stop()


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


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Press Intelligence")
    st.caption("StatsBomb open data · La Liga 2015/16")

    with st.expander("ⓘ What this module does"):
        st.markdown(
            """
**Press Intelligence** answers three coach questions:

1. **Trigger** — when is our press working? *(Press Timeline)*
2. **Release** — when should we drop into a block? *(PPDA collapsing)*
3. **Substitute** — who will sustain the press? *(Substitution Profiles)*

It uses StatsBomb event data to compute **PPDA** (Passes Allowed per
Defensive Action) in 10-minute windows across the match.
**Low PPDA = effective press.** High PPDA = opponent playing through it.
            """
        )

    selected_label = st.selectbox("Select Match", matches_df["_label"].tolist(), key="pi_match")
    sel_row      = matches_df[matches_df["_label"] == selected_label].iloc[0]
    home_team    = sel_row["_home"]
    away_team    = sel_row["_away"]
    match_id     = int(sel_row["match_id"])

    our_team      = st.radio("Analyse press for:", [home_team, away_team])
    opponent_team = away_team if our_team == home_team else home_team

    threshold = st.slider(
        "PPDA collapse threshold",
        min_value=6.0, max_value=16.0,
        value=float(PPDA_COLLAPSE_THRESHOLD),
        step=0.5,
        help=(
            "Above this value the press is considered broken. "
            "Default 10.0 is backtested against La Liga 2015/16 goal data. "
            "Adjust for different leagues or playing styles."
        ),
    )


# ── Page title ────────────────────────────────────────────────────────────────
st.title("🔍 Press Intelligence")
st.markdown(
    f"<span style='font-size:1.1rem;color:{COLORS['muted']};'>"
    f"{home_team} vs {away_team} &nbsp;·&nbsp; "
    f"Analysing: <b style='color:{COLORS['text']};'>{our_team}</b>"
    f" &nbsp;·&nbsp; Threshold: <b style='color:{COLORS['text']};'>{threshold}</b>"
    f"</span>",
    unsafe_allow_html=True,
)
st.divider()


# ── Compute windows (both perspectives) ──────────────────────────────────────
try:
    win_df     = _cached_windows(match_id, our_team, opponent_team)
    opp_win_df = _cached_windows(match_id, opponent_team, our_team)
except Exception as e:
    st.error(f"Could not compute press windows: {e}")
    st.stop()

if win_df.empty:
    st.warning("No window data available for this match.")
    st.stop()

labels = win_df["window_label"].tolist()


# ── Load raw events for goal / red-card annotations ──────────────────────────
try:
    raw_ev = _cached_events(match_id)
except Exception:
    raw_ev = pd.DataFrame()

def _goals_from_events(ev: pd.DataFrame) -> pd.DataFrame:
    if ev.empty or "type_name" not in ev.columns:
        return pd.DataFrame()
    mask = (ev["type_name"] == "Shot") & (ev.get("shot_outcome", pd.Series("", index=ev.index)) == "Goal")
    return ev[mask][["minute", "team_name", "player"]].copy() if mask.any() else pd.DataFrame()

def _red_cards_from_events(ev: pd.DataFrame) -> pd.DataFrame:
    if ev.empty or "type_name" not in ev.columns:
        return pd.DataFrame()
    # StatsBomb stores red cards as 'Bad Behaviour' events
    mask = ev["type_name"] == "Bad Behaviour"
    if not mask.any():
        return pd.DataFrame()
    rc = ev[mask].copy()
    # Card column may be 'bad_behaviour_card' or similar
    card_col = next((c for c in rc.columns if "bad_behaviour" in c and "card" in c), None)
    if card_col:
        rc = rc[rc[card_col].astype(str).str.contains("Red", na=False)]
    return rc[["minute", "team_name", "player"]].copy() if not rc.empty else pd.DataFrame()

goals_ev    = _goals_from_events(raw_ev)
red_card_ev = _red_cards_from_events(raw_ev)


def _minute_to_window_label(minute: int) -> str:
    w = (minute // 10) * 10
    return f"{w}–{w + 10}'"


# ── Summary KPIs ─────────────────────────────────────────────────────────────
valid_wins   = win_df[win_df["sufficient_data"]]
direct_wins  = win_df[win_df["build_up_tendency"] == CATEGORY_DIRECT]

avg_ppda_bu = (
    valid_wins[valid_wins["build_up_tendency"] != CATEGORY_DIRECT]["ppda"]
    .dropna().mean()
)
avg_mom      = win_df["momentum_index"].dropna().mean()
n_direct     = len(direct_wins)
n_total      = len(win_df)
direct_pct   = n_direct / max(n_total, 1)
avg_sb_rate  = direct_wins["second_ball_recovery_rate"].mean() if not direct_wins.empty else 0.0
avg_psr      = valid_wins["pressing_success_rate"].mean() if not valid_wins.empty else 0.0

kpi_row([
    kpi_card(
        "Avg PPDA (Build-up windows)",
        f"{avg_ppda_bu:.1f}" if not np.isnan(avg_ppda_bu) else "—",
        sub="excl. Direct/Defensive", accent=COLORS["primary"],
    ),
    kpi_card(
        "Direct/Defensive Windows",
        f"{n_direct}/{n_total}",
        sub=f"{direct_pct:.0%} of match", accent=COLORS["secondary"],
    ),
    kpi_card(
        "2nd-Ball Recovery Rate",
        f"{avg_sb_rate:.0%}" if not direct_wins.empty else "—",
        sub="Direct windows only", accent=COLORS["warning"],
    ),
    kpi_card(
        "Pressing Success Rate",
        f"{avg_psr:.0%}",
        sub="regains / pressures", accent=COLORS["success"],
    ),
    kpi_card(
        "Avg Momentum Index",
        f"{avg_mom:.0f}/100" if not np.isnan(avg_mom) else "—",
        sub="0 = poor · 100 = dominant", accent=COLORS["primary"],
    ),
])

with st.columns([18, 1])[1]:
    info_popover(
        "**Avg PPDA (Build-up windows)** — lower is better. Excludes Direct/Defensive "
        "windows where the opponent barely built through their zone (PPDA is unreliable there).\n\n"
        "**2nd-Ball Recovery Rate** — in Direct/Defensive windows, how often did we win the "
        "ball within 5 seconds of an opponent clearance or long ball?\n\n"
        "**Pressing Success Rate** — % of our pressure events that led to a turnover within 5s.\n\n"
        "**Momentum Index** — composite score combining PPDA performance (60%) and territory "
        "depth (40%). It's a heuristic summary — read the full charts before acting on it."
    )

st.markdown("<br>", unsafe_allow_html=True)

# Strategy text
if direct_pct > 0.5:
    st.info(
        f"**Opponent played direct:** {direct_pct:.0%} of windows are Direct/Defensive — "
        f"{opponent_team} rarely built through their zone. PPDA understates press difficulty. "
        f"**2nd-ball recovery rate ({avg_sb_rate:.0%}) is the primary signal** — "
        f"focus on positioning for second balls rather than high-line pressing."
    )
elif direct_pct > 0.25:
    st.warning(
        f"**Mixed match:** {direct_pct:.0%} of windows show direct play. "
        f"Monitor PPDA (avg {avg_ppda_bu:.1f}) and 2nd-ball recovery ({avg_sb_rate:.0%}) together."
    )
else:
    verdict = "effective" if not np.isnan(avg_ppda_bu) and avg_ppda_bu <= threshold else "under pressure"
    st.success(
        f"**Genuine build-up match:** {opponent_team} built through their zone. "
        f"PPDA is a reliable signal — press is **{verdict}** (avg {avg_ppda_bu:.1f}, threshold {threshold})."
    )

st.markdown("<br>", unsafe_allow_html=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_timeline, tab_context, tab_momentum, tab_subs, tab_history, tab_validator = st.tabs([
    "📊 Press Timeline",
    "🗂 Context Layer",
    "📈 Momentum Index",
    "👤 Substitution Profiles",
    "📋 Opponent History",
    "✅ Threshold Validator",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — PRESS TIMELINE  (our press + opponent press side by side)
# ════════════════════════════════════════════════════════════════════════════════
with tab_timeline:
    section_header(
        "PPDA Press Timeline", icon="📊",
        subtitle="10-minute windows · teal = good press · amber = collapsing · hatched = Direct/Defensive",
        help_text=(
            "**PPDA** (Passes Allowed per Defensive Action) measures how many passes the opponent "
            "completes in their own defensive zone for each defensive action we make there. "
            "<br><br>"
            "**Low PPDA = effective press** — we're winning the ball back quickly. "
            "**High PPDA = press broken** — they're playing through us comfortably. "
            "<br><br>"
            "**Hatched bars** = Direct/Defensive windows where the opponent rarely passed through "
            "their zone by design, so PPDA is not a reliable signal. Use 2nd-ball recovery rate instead. "
            "<br><br>"
            "**⚽ / 🟥 markers** = goals and red cards — critical context for any PPDA shift."
        ),
    )

    info_box(
        "Left chart: <b>our team pressing</b>. Right chart: <b>opponent pressing</b>. "
        "When our PPDA is low while theirs is high — that's the window to push tempo."
    )

    def _build_timeline_fig(wdf: pd.DataFrame, pressing_team: str, thresh: float) -> go.Figure:
        lbls = wdf["window_label"].tolist()
        y_good, y_poor, y_insuff, y_direct = [], [], [], []
        hover_texts = []

        for _, row in wdf.iterrows():
            ppda = row["ppda"]
            suff = row["sufficient_data"]
            tend = row["build_up_tendency"]
            null = ppda is None or (isinstance(ppda, float) and np.isnan(ppda))

            if not suff or null:
                y_good.append(None); y_poor.append(None)
                y_insuff.append(MIN_EVENTS_GREY_OUT * 0.5); y_direct.append(None)
                hover_texts.append(f"<b>{row['window_label']}</b><br>Insufficient data")
            elif tend == CATEGORY_DIRECT:
                y_good.append(None); y_poor.append(None); y_insuff.append(None)
                y_direct.append(float(ppda))
                hover_texts.append(
                    f"<b>{row['window_label']}</b><br>"
                    f"PPDA: {ppda:.1f} (unreliable — direct play)<br>"
                    f"2nd-ball recovery: {row['second_ball_recovery_rate']:.0%}"
                )
            elif float(ppda) <= thresh:
                y_good.append(float(ppda)); y_poor.append(None)
                y_insuff.append(None); y_direct.append(None)
                hover_texts.append(
                    f"<b>{row['window_label']}</b><br>PPDA: {ppda:.1f} ✓<br>"
                    f"Zone passes: {row['opp_zone_passes']} · Actions: {row['our_defensive_actions']}<br>"
                    f"Press success: {row['pressing_success_rate']:.0%}"
                )
            else:
                y_good.append(None); y_poor.append(float(ppda))
                y_insuff.append(None); y_direct.append(None)
                hover_texts.append(
                    f"<b>{row['window_label']}</b><br>PPDA: {ppda:.1f} ⚠<br>"
                    f"Zone passes: {row['opp_zone_passes']} · Actions: {row['our_defensive_actions']}<br>"
                    f"Press success: {row['pressing_success_rate']:.0%}"
                )

        fig = go.Figure()
        kw  = dict(x=lbls, showlegend=True)
        fig.add_trace(go.Bar(**kw, name="Good press",   y=y_good,
                             marker=dict(color=_TEAL, opacity=0.9),
                             hovertext=hover_texts, hoverinfo="text"))
        fig.add_trace(go.Bar(**kw, name="Collapsing",   y=y_poor,
                             marker=dict(color=_AMBER, opacity=0.9),
                             hovertext=hover_texts, hoverinfo="text"))
        fig.add_trace(go.Bar(**kw, name="Direct/Def.",  y=y_direct,
                             marker=dict(color=_MUTED, opacity=0.7,
                                         pattern=dict(shape="/", fgcolor="rgba(255,255,255,0.4)", size=6)),
                             hovertext=hover_texts, hoverinfo="text"))
        fig.add_trace(go.Bar(**kw, name="Low data",     y=y_insuff,
                             marker=dict(color=_GREY, opacity=0.4),
                             hovertext=hover_texts, hoverinfo="text"))
        fig.add_hline(y=thresh, line_dash="dash", line_color=COLORS["danger"],
                      annotation_text=f"Threshold ({thresh})",
                      annotation_font_color=COLORS["danger"])
        fig.update_layout(barmode="overlay", title=dict(
            text=f"{pressing_team} pressing",
            font=dict(color=COLORS["text"], size=13),
        ))
        return style_chart(
            fig, height=320,
            xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
            yaxis=dict(title="PPDA  (lower = better)", gridcolor=COLORS["grid"]),
        )

    # Annotate goal / red-card events on a figure
    def _annotate_events(fig: go.Figure, wdf: pd.DataFrame,
                         goals: pd.DataFrame, reds: pd.DataFrame,
                         pressing_team: str) -> go.Figure:
        for evdf, symbol, our_color, opp_color, label_fn in [
            (goals, "star", COLORS["success"], COLORS["danger"],
             lambda r: f"⚽ {r.get('player','?')} ({int(r['minute'])}')"),
            (reds,  "x",    COLORS["danger"],  COLORS["warning"],
             lambda r: f"🟥 {r.get('player','?')} ({int(r['minute'])}')"),
        ]:
            if evdf.empty:
                continue
            for _, row in evdf.iterrows():
                wlabel = _minute_to_window_label(int(row.get("minute", 0)))
                w_rows = wdf[wdf["window_label"] == wlabel]
                if w_rows.empty:
                    continue
                ppda = w_rows.iloc[0]["ppda"]
                y    = float(ppda) if (ppda is not None and not np.isnan(ppda)) else 3.0
                team = str(row.get("team_name", ""))
                color = our_color if team == pressing_team else opp_color
                fig.add_trace(go.Scatter(
                    x=[wlabel], y=[y + 1.2],
                    mode="markers",
                    marker=dict(symbol=symbol, size=13, color=color,
                                line=dict(width=1.5, color=COLORS["bg"])),
                    name=label_fn(row),
                    showlegend=False,
                    hovertemplate=f"<b>{label_fn(row)}</b><br>{team}<extra></extra>",
                ))
        return fig

    col_l, col_r = st.columns(2)
    with col_l:
        fig_ours = _build_timeline_fig(win_df, our_team, threshold)
        fig_ours = _annotate_events(fig_ours, win_df, goals_ev, red_card_ev, our_team)
        st.plotly_chart(fig_ours, width="stretch")

    with col_r:
        if not opp_win_df.empty:
            fig_opp = _build_timeline_fig(opp_win_df, opponent_team, threshold)
            fig_opp = _annotate_events(fig_opp, opp_win_df, goals_ev, red_card_ev, opponent_team)
            st.plotly_chart(fig_opp, width="stretch")
        else:
            st.info(f"No window data for {opponent_team}'s press.")

    # Direct/Defensive detail table
    if not direct_wins.empty:
        st.markdown("#### Direct/Defensive Windows — Alternative Metric")
        st.caption("When the opponent plays direct, PPDA is unreliable. Use 2nd-ball recovery rate instead.")
        detail = direct_wins[[
            "window_label", "opp_zone_passes", "long_pass_ratio",
            "second_ball_recovery_rate", "second_ball_recoveries",
        ]].copy()
        detail.columns = ["Window", "Opp Zone Passes", "Long-Pass Ratio",
                          "2nd-Ball Recovery", "Recoveries"]
        detail["Long-Pass Ratio"]    = detail["Long-Pass Ratio"].map("{:.0%}".format)
        detail["2nd-Ball Recovery"]  = detail["2nd-Ball Recovery"].map("{:.0%}".format)
        st.dataframe(detail, width="stretch", hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — CONTEXT LAYER
# ════════════════════════════════════════════════════════════════════════════════
with tab_context:
    section_header(
        "Context Layer", icon="🗂",
        subtitle="Possession · Pressing Success · Defensive Territory Depth",
        help_text=(
            "These three metrics explain **why** PPDA is doing what it's doing. "
            "They don't replace the press signal — they answer the follow-up question. "
            "<br><br>"
            "**Possession by Period** — a press can look broken simply because your team had "
            "the ball; high PPDA with high possession is not necessarily a collapse. "
            "<br><br>"
            "**Pressing Success Rate** — PPDA tells you how often they pass through the press; "
            "this tells you how often the press actually worked when triggered. 30%+ is strong. "
            "<br><br>"
            "**Territory Depth** — average x-coordinate of our defensive actions per window. "
            "Below 60m = mid-block; above 80m = genuine high press. "
            "A dropping depth number often precedes a PPDA rise — it's the early warning signal."
        ),
    )

    c1, c2 = st.columns(2)

    with c1:
        section_header("Possession by Period", icon="🔵")
        fig_poss = go.Figure()
        fig_poss.add_trace(go.Bar(x=labels, y=win_df["our_poss_share"] * 100,
                                   name=our_team, marker_color=_TEAL, opacity=0.85))
        fig_poss.add_trace(go.Bar(x=labels, y=win_df["opp_poss_share"] * 100,
                                   name=opponent_team, marker_color=_AMBER, opacity=0.65))
        fig_poss.add_hline(y=50, line_dash="dot", line_color=_GREY)
        fig_poss = style_chart(fig_poss, height=260, barmode="group",
                                yaxis=dict(title="Possession %", range=[0, 100],
                                           gridcolor=COLORS["grid"]),
                                xaxis=dict(title="Window", gridcolor=COLORS["grid"]))
        st.plotly_chart(fig_poss, width="stretch")

        section_header("Pressing Success Rate", icon="🎯",
                       help_text=(
                           "% of pressure events followed by a turnover within 5 seconds. "
                           "<br>**30%+** = strong press · **15–30%** = moderate · **&lt;15%** = press triggering but not winning the ball. "
                           "<br><br>A high success rate with a high PPDA means your press is disorganised; "
                           "a low success rate with low PPDA means you're applying lots of pressure but the opponent is coping."
                       ))
        psr_colors = [
            _TEAL if r >= 0.30 else _AMBER if r >= 0.15 else _GREY
            for r in win_df["pressing_success_rate"]
        ]
        fig_psr = go.Figure(go.Bar(x=labels, y=win_df["pressing_success_rate"] * 100,
                                    marker_color=psr_colors, opacity=0.9,
                                    hovertemplate="%{x}<br>Success: %{y:.1f}%<extra></extra>"))
        fig_psr.add_hline(y=30, line_dash="dash", line_color=_TEAL,
                          annotation_text="30% benchmark", annotation_font_color=_TEAL)
        fig_psr = style_chart(fig_psr, height=240,
                               yaxis=dict(title="Success Rate %", gridcolor=COLORS["grid"]),
                               xaxis=dict(title="Window", gridcolor=COLORS["grid"]))
        st.plotly_chart(fig_psr, width="stretch")

    with c2:
        section_header("Defensive Territory Depth", icon="🛡️",
                       help_text=(
                           "Average x-coordinate (StatsBomb: 0–120m) of our defensive actions per window. "
                           "Higher = pressing further up the pitch. "
                           "<br><br>"
                           "**&lt; 60m** = defending in our own half (mid-block or deep block) "
                           "<br>**60–80m** = midfield press "
                           "<br>**&gt; 80m** = genuine high press in the opponent's half "
                           "<br><br>"
                           "Watch for a downward trend across windows — this often precedes a PPDA rise "
                           "and is an early warning signal that the press is fading."
                       ))
        info_box("Higher = our defensive actions occur further up the pitch. "
                 "A dropping trend often precedes a PPDA collapse.")
        depth_colors = [
            _TEAL if d >= 70 else _AMBER if d >= 50 else COLORS["danger"]
            for d in win_df["territory_depth"]
        ]
        fig_depth = go.Figure(go.Bar(x=labels, y=win_df["territory_depth"],
                                      marker_color=depth_colors, opacity=0.85,
                                      hovertemplate="%{x}<br>Depth: %{y:.0f}m<extra></extra>"))
        fig_depth.add_hline(y=60, line_dash="dot", line_color=_GREY, annotation_text="Midfield")
        fig_depth.add_hline(y=80, line_dash="dash", line_color=_TEAL, annotation_text="High press zone")
        fig_depth = style_chart(fig_depth, height=260,
                                 yaxis=dict(title="Avg x of defensive actions (m)",
                                            range=[0, 120], gridcolor=COLORS["grid"]),
                                 xaxis=dict(title="Window", gridcolor=COLORS["grid"]))
        st.plotly_chart(fig_depth, width="stretch")

        section_header("2nd-Ball Recovery by Third", icon="⚽",
                       help_text=(
                           "After an opponent clearance or long ball in their defensive zone, "
                           "which third of the pitch did we win the second ball? "
                           "<br><br>"
                           "**Attacking third** recoveries are most dangerous and signal a high press that's winning second balls. "
                           "<br>**Defensive third** recoveries mean we're conceding the first touch and fighting for it deep."
                       ))
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
        fig_thirds = style_chart(fig_thirds, height=240)
        fig_thirds.update_traces(textfont_color=COLORS["text"])
        st.plotly_chart(fig_thirds, width="stretch")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — MOMENTUM INDEX
# ════════════════════════════════════════════════════════════════════════════════
with tab_momentum:
    section_header(
        "Match Momentum Index", icon="📈",
        subtitle=f"PPDA component (60%) + Territory Depth (40%) — composite 0–100 score per window",
        help_text=(
            "A single score per 10-minute window combining two signals: "
            "<br><br>"
            "**PPDA score (60% weight)** — 100 when PPDA → 0 (perfect press), "
            "50 at the collapse threshold, 0 at 2× threshold. "
            "<br><br>"
            "**Territory score (40% weight)** — (territory depth / 120m) × 100. "
            "Higher x position = higher score. "
            "<br><br>"
            "**⚠ Heuristic only** — this formula is documented but has not been validated against "
            "outcomes. Always read the underlying PPDA and territory charts. "
            f"Direct/Defensive windows have their PPDA component down-weighted by "
            f"{int(DIRECT_PPDA_WEIGHT_FACTOR * 100)}% to prevent an artefactually low PPDA "
            f"from inflating the score."
        ),
    )

    info_box(
        f"<b>Heuristic summary</b> — the index combines PPDA and territory depth into one number. "
        f"It is explicitly labelled as a heuristic: read the underlying charts, not just the index. "
        f"Direct/Defensive windows (◆) have their PPDA weight reduced by "
        f"{int((1 - DIRECT_PPDA_WEIGHT_FACTOR) * 100)}% to avoid false high scores."
    )

    mom_vals  = win_df["momentum_index"].tolist()
    tend_list = win_df["build_up_tendency"].tolist()
    suff_list = win_df["sufficient_data"].tolist()

    fig_mom = go.Figure()
    for label, mom, tend, suff in zip(labels, mom_vals, tend_list, suff_list):
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
                f"<b>{label}</b><br>Momentum: {mom:.0f}/100<br>"
                f"Tendency: {tend}<extra></extra>"
            ),
        ))

    valid_mom = [
        (l, m) for l, m, s in zip(labels, mom_vals, suff_list)
        if s and m is not None and not (isinstance(m, float) and np.isnan(m))
    ]
    if valid_mom:
        xl, yl = zip(*valid_mom)
        fig_mom.add_trace(go.Scatter(
            x=list(xl), y=list(yl), mode="lines",
            line=dict(color=COLORS["primary"], width=2, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))

    fig_mom.add_hline(y=50, line_dash="dash", line_color=_GREY,
                      annotation_text="Neutral (50)", annotation_font_color=_GREY)
    fig_mom = style_chart(fig_mom, height=360,
                           xaxis=dict(title="Window", gridcolor=COLORS["grid"]),
                           yaxis=dict(title="Momentum Index (0–100)", range=[0, 105],
                                      gridcolor=COLORS["grid"]))
    st.plotly_chart(fig_mom, width="stretch")

    st.markdown(
        f"<small style='color:{_TEAL}'>● Good press (≥ 60)</small> &nbsp; "
        f"<small style='color:{_AMBER}'>● Under pressure (&lt; 60)</small> &nbsp; "
        f"<small style='color:{_MUTED}'>◆ Direct/Defensive (PPDA down-weighted)</small> &nbsp; "
        f"<small style='color:{_GREY}'>● Insufficient data</small>",
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    mom_table = win_df[[
        "window_label", "build_up_tendency", "ppda",
        "territory_depth", "momentum_index", "sufficient_data",
    ]].copy()
    mom_table.columns = ["Window", "Build-up Tendency", "PPDA",
                          "Territory (m)", "Momentum", "Sufficient Data"]
    mom_table["PPDA"]     = mom_table["PPDA"].apply(
        lambda v: f"{v:.1f}" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "—")
    mom_table["Momentum"] = mom_table["Momentum"].apply(
        lambda v: f"{v:.0f}" if v is not None else "—")
    st.dataframe(mom_table, width="stretch", hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — SUBSTITUTION PRESSING PROFILES
# ════════════════════════════════════════════════════════════════════════════════
with tab_subs:
    section_header(
        "Substitution Pressing Profiles", icon="👤",
        subtitle="Compare two players' pressing contributions across cached La Liga 2015/16 matches",
        help_text=(
            "Use this to decide who to bring on to sustain or restart the press. "
            "<br><br>"
            "**Pressures/Match** — average number of pressure events per appearance. "
            "High = pressing machine. Low = conserves energy for other roles. "
            "<br><br>"
            "**Regain Rate** — % of a player's pressures that led to the team winning "
            "the ball within 5 seconds. High rate = pressing in the right areas, not just volume. "
            "<br><br>"
            "**Late Pressures/Match** — average pressures in the last 20 minutes of each "
            "appearance. This is the key substitution signal — a player who presses as hard "
            "in minute 80 as minute 10 maintains press intensity when others fatigue. "
            "<br><br>"
            "⚠ Stats are computed from locally cached matches only. Players with fewer than "
            "2 cached appearances are excluded. This is not per-90 (exact minutes unavailable "
            "from StatsBomb events alone) — treat it as relative ranking, not absolute."
        ),
    )

    info_box(
        "Computed from all locally cached La Liga 2015/16 event files. "
        "Filter by team below, then select two players to compare side-by-side. "
        "More cached matches = more reliable profiles."
    )

    profiles_df = _build_pressing_profiles()

    if profiles_df.empty:
        st.warning("No pressing profiles available — no event files cached yet. Select a match in the sidebar to cache its events.")
    else:
        # Team filter
        all_teams = sorted(profiles_df["team"].unique().tolist())
        team_filter = st.selectbox(
            "Filter by team (optional)",
            ["All teams"] + all_teams,
            key="sub_team_filter",
        )
        display_df = profiles_df if team_filter == "All teams" else profiles_df[profiles_df["team"] == team_filter]

        player_list = display_df["player"].tolist()
        if len(player_list) < 2:
            st.info("Not enough players with 2+ cached appearances for comparison.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                player_a = st.selectbox("Player A", player_list, key="sub_a")
            with c2:
                default_b = player_list[1] if player_list[0] == player_a else player_list[0]
                player_b = st.selectbox("Player B", player_list,
                                         index=player_list.index(default_b) if default_b in player_list else 1,
                                         key="sub_b")

            row_a = display_df[display_df["player"] == player_a].iloc[0]
            row_b = display_df[display_df["player"] == player_b].iloc[0]

            # Radar / bar comparison
            metrics      = ["press_per_match", "regain_rate", "late_per_match"]
            metric_labels = ["Press/Match", "Regain Rate", "Late Press/Match"]
            vals_a = [float(row_a[m]) for m in metrics]
            vals_b = [float(row_b[m]) for m in metrics]

            # Normalise for radar (0–1 within the displayed group)
            max_vals = [max(display_df[m].max(), 1e-6) for m in metrics]
            norm_a   = [v / mx for v, mx in zip(vals_a, max_vals)]
            norm_b   = [v / mx for v, mx in zip(vals_b, max_vals)]

            fig_radar = go.Figure()
            for norm, raw, name, color in [
                (norm_a, vals_a, player_a, _TEAL),
                (norm_b, vals_b, player_b, _AMBER),
            ]:
                closed_norm = norm + [norm[0]]
                closed_labels = metric_labels + [metric_labels[0]]
                fig_radar.add_trace(go.Scatterpolar(
                    r=closed_norm, theta=closed_labels,
                    fill="toself", name=name,
                    line=dict(color=color, width=2),
                    marker=dict(color=color),
                    hovertemplate=(
                        f"<b>{name}</b><br>"
                        + "<br>".join(f"{l}: {v:.2f}" for l, v in zip(metric_labels, raw))
                        + "<extra></extra>"
                    ),
                ))
            fig_radar = style_chart(fig_radar, height=320)
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1],
                                    showticklabels=False, gridcolor=COLORS["grid"]),
                    angularaxis=dict(gridcolor=COLORS["grid"]),
                    bgcolor=COLORS["surface"],
                ),
            )
            st.plotly_chart(fig_radar, width="stretch")

            # Side-by-side stats table
            compare = pd.DataFrame({
                "Metric": metric_labels + ["Matches", "Total Pressures"],
                player_a: [
                    f"{vals_a[0]:.1f}", f"{vals_a[1]:.1%}", f"{vals_a[2]:.1f}",
                    str(int(row_a["matches"])), str(int(row_a["total_press"])),
                ],
                player_b: [
                    f"{vals_b[0]:.1f}", f"{vals_b[1]:.1%}", f"{vals_b[2]:.1f}",
                    str(int(row_b["matches"])), str(int(row_b["total_press"])),
                ],
            })
            st.dataframe(compare, width="stretch", hide_index=True)

            # Full ranked table
            with st.expander("All players — ranked by Pressures/Match"):
                display_cols = {
                    "player": "Player", "team": "Team",
                    "matches": "Matches", "press_per_match": "Press/Match",
                    "regain_rate": "Regain Rate", "late_per_match": "Late/Match",
                }
                tbl = display_df[list(display_cols)].rename(columns=display_cols)
                tbl["Regain Rate"] = tbl["Regain Rate"].map("{:.1%}".format)
                st.dataframe(tbl, width="stretch", hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — OPPONENT SEASON PRESS HISTORY
# ════════════════════════════════════════════════════════════════════════════════
with tab_history:
    section_header(
        "Opponent Season Press History", icon="📋",
        subtitle=f"Season-long PPDA trend for {opponent_team} as pressing team (cached matches only)",
        help_text=(
            "Shows how effectively the opponent presses across the season — not just against you. "
            "<br><br>"
            "A team whose PPDA rises consistently after minute 60 **across many matches** "
            "is showing a structural weakness, not a one-off. That pattern is actionable: "
            "absorb their press early and push tempo in the second half. "
            "<br><br>"
            "Only matches whose events are locally cached are shown. "
            "The sample size is displayed below the chart — "
            "patterns from &lt;5 matches should be treated as preliminary."
        ),
    )

    info_box(
        f"Showing {opponent_team}'s press performance as the pressing team across cached La Liga 2015/16 matches. "
        "Each point = one match. The dashed line = your current match's threshold."
    )

    hist_df = _opponent_history(opponent_team)

    if hist_df.empty:
        st.info(
            f"No cached matches found for {opponent_team} yet. "
            "Select and load some of their matches from the sidebar to build the history."
        )
    else:
        fig_hist = go.Figure()
        bar_colors = [
            _TEAL if v <= threshold else _AMBER
            for v in hist_df["Avg PPDA"]
        ]

        # Highlight current match
        current_point = hist_df[hist_df["match_id"] == match_id]

        fig_hist.add_trace(go.Bar(
            x=hist_df["Date"],
            y=hist_df["Avg PPDA"],
            marker_color=bar_colors, opacity=0.8,
            customdata=hist_df[["Opponent", "H/A"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "vs %{customdata[0]} (%{customdata[1]})<br>"
                "Avg PPDA: %{y:.2f}<extra></extra>"
            ),
        ))

        if not current_point.empty:
            fig_hist.add_trace(go.Scatter(
                x=current_point["Date"], y=current_point["Avg PPDA"],
                mode="markers",
                marker=dict(size=14, color=COLORS["primary"],
                            symbol="star", line=dict(width=2, color=COLORS["bg"])),
                name="Current match",
                hovertemplate="<b>Current match</b><br>PPDA: %{y:.2f}<extra></extra>",
            ))

        fig_hist.add_hline(y=threshold, line_dash="dash", line_color=COLORS["danger"],
                            annotation_text=f"Threshold ({threshold})",
                            annotation_font_color=COLORS["danger"])

        season_avg = hist_df["Avg PPDA"].mean()
        fig_hist.add_hline(y=season_avg, line_dash="dot", line_color=_GREY,
                            annotation_text=f"Season avg ({season_avg:.1f})",
                            annotation_font_color=_GREY)

        fig_hist = style_chart(fig_hist, height=340,
                                xaxis=dict(title="Match Date", gridcolor=COLORS["grid"]),
                                yaxis=dict(title=f"Avg PPDA ({opponent_team} pressing)",
                                           gridcolor=COLORS["grid"]))
        st.plotly_chart(fig_hist, width="stretch")

        n_matches = len(hist_df)
        below_thresh = (hist_df["Avg PPDA"] <= threshold).sum()
        st.caption(
            f"Based on **{n_matches} cached match(es)**. "
            f"{below_thresh}/{n_matches} matches had avg PPDA ≤ {threshold} (good press). "
            f"Season average: {season_avg:.2f}."
        )

        st.dataframe(
            hist_df[["Date", "Opponent", "H/A", "Avg PPDA"]],
            width="stretch", hide_index=True,
        )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 6 — THRESHOLD VALIDATOR
# ════════════════════════════════════════════════════════════════════════════════
with tab_validator:
    section_header(
        "Threshold Validator", icon="✅",
        subtitle="Backtested against La Liga 2015/16 (up to 380 matches)",
        help_text=(
            "This validator runs the PPDA engine across all available La Liga 2015/16 matches "
            "and reports the distribution of window categories. "
            "<br><br>"
            "**Why this matters:** a collapse threshold is only worth using if it separates "
            "something meaningful. The validator confirms what fraction of windows are Build-up, "
            "Mixed, or Direct/Defensive — justifying which windows PPDA should be applied to. "
            "<br><br>"
            "The PPDA distribution (mean, std, quartiles) shows where the current threshold "
            "sits relative to the full season. The default 10.0 is derived from this data."
        ),
    )

    info_box(
        "Runs the PPDA engine across all cached La Liga 2015/16 matches. "
        "Results are cached after the first run — click <b>Run / Refresh</b> to update."
    )

    if st.button("Run / Refresh Threshold Validator", type="primary"):
        with st.spinner("Running validator across all La Liga 2015/16 matches…"):
            results = _cached_validator()
        st.session_state["validator_results"] = results

    if "validator_results" in st.session_state:
        results = st.session_state["validator_results"]
        if "error" in results:
            st.error(results["error"])
        else:
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Matches processed", results.get("n_matches", "—"))
            v2.metric("Total windows",     results.get("n_windows_total", "—"))
            v3.metric("Valid windows",     results.get("n_windows_valid", "—"))
            v4.metric("Threshold used",    f"PPDA = {results.get('collapse_threshold', PPDA_COLLAPSE_THRESHOLD)}")

            st.markdown("#### PPDA Distribution (Build-up + Mixed windows)")
            p1, p2, p3, p4 = st.columns(4)
            p1.metric("Mean PPDA",    results.get("ppda_mean", "—"))
            p2.metric("Std Dev",      results.get("ppda_std",  "—"))
            p3.metric("25th pctile",  results.get("ppda_p25",  "—"))
            p4.metric("75th pctile",  results.get("ppda_p75",  "—"))

            st.markdown("#### Build-up Category Distribution (all valid windows)")
            cat_dist = results.get("category_distribution", {})
            if cat_dist:
                cat_rows = []
                for cat in [CATEGORY_BUILDUP, CATEGORY_MIXED, CATEGORY_DIRECT]:
                    info = cat_dist.get(cat, {"count": 0, "fraction": 0.0})
                    cat_rows.append({
                        "Category": cat,
                        "Windows":  info["count"],
                        "Fraction": f"{info['fraction']:.1%}",
                        "Note": (
                            "Normal PPDA scoring"
                            if cat != CATEGORY_DIRECT
                            else "2nd-ball recovery used; PPDA down-weighted"
                        ),
                    })
                st.dataframe(pd.DataFrame(cat_rows), width="stretch", hide_index=True)

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
                st.plotly_chart(fig_cat, width="stretch")

                direct_frac = cat_dist.get(CATEGORY_DIRECT, {}).get("fraction", 0)
                st.success(
                    f"**{direct_frac:.1%}** of analysed windows were classified Direct/Defensive — "
                    f"excluded from PPDA-based momentum scoring. Second-ball recovery rate used instead."
                )
    else:
        st.info("Click **Run / Refresh Threshold Validator** to backtest. Results are cached after the first run.")
