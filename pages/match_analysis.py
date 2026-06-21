"""
Match Analysis - La Liga 2015/16 (StatsBomb)
============================================
Shot map · xG timeline (both teams) · Press breakdown.

StatsBomb coordinate notes
--------------------------
Events are stored in a team-relative coordinate system: x=0 is own goal,
x=120 is the opponent's goal.  All shot x values therefore cluster near
x=120 regardless of period or team - no direction-flip is needed.
Pressures span 0–120 because they happen across the full pitch.
Scale to pitch drawing: x_plot = x * 105/120, y_plot = y * 68/80.

Shot outcome strings from StatsBomb open data:
  'Goal', 'Saved', 'Blocked', 'Off T', 'Wayward', 'Post'
  on_target  ← {'Goal', 'Saved'}
  goal       ← {'Goal'}
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

import ui.styles as styles
from ui.components import kpi_card, kpi_row, section_header, style_chart, draw_pitch, info_box, info_popover
from config import COLORS

from analytics.press_engine import (
    load_sb_matches,
    load_match_events,
    SB_AVAILABLE,
    SB_PITCH_LEN,
    SB_PITCH_WID,
)

styles.apply()

# ── StatsBomb availability guard ──────────────────────────────────────────────
if not SB_AVAILABLE:
    st.error(
        "**statsbombpy is not installed.**  "
        "Run `pip install statsbombpy` and restart."
    )
    st.stop()

# ── Cache wrappers ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading La Liga 2015/16 matches…")
def _cached_matches() -> pd.DataFrame:
    return load_sb_matches()


@st.cache_data(show_spinner="Loading match events…")
def _cached_events(match_id: int) -> pd.DataFrame:
    return load_match_events(match_id)


# ── Team name extraction (handles dict or plain string) ───────────────────────
def _tn(val) -> str:
    if isinstance(val, dict):
        for k in ("home_team_name", "away_team_name", "name"):
            if k in val:
                return val[k]
    return str(val) if pd.notna(val) else ""


# ── Load La Liga 2015/16 matches ──────────────────────────────────────────────
try:
    matches_df = _cached_matches()
except Exception as exc:
    st.error(f"Could not load La Liga 2015/16 matches: {exc}")
    st.stop()

if matches_df.empty:
    st.warning("No matches found for La Liga 2015/16.")
    st.stop()

matches_df["_home"] = matches_df.get(
    "home_team", pd.Series("", index=matches_df.index)
).apply(_tn)
matches_df["_away"] = matches_df.get(
    "away_team", pd.Series("", index=matches_df.index)
).apply(_tn)


def _match_label(row) -> str:
    date = str(row.get("match_date", row.get("match_week", "")))
    hs   = row.get("home_score", "?")
    as_  = row.get("away_score", "?")
    return f"{row['_home']}  {hs}–{as_}  {row['_away']}  [{date}]"


matches_df["_label"] = matches_df.apply(_match_label, axis=1)

with st.sidebar:
    st.markdown("### ⚽ Match Analysis")
    st.caption("StatsBomb open data · La Liga 2015/16")
    selected_label = st.selectbox("Select Match", matches_df["_label"].tolist(), key="ma_match")
    sel_row    = matches_df[matches_df["_label"] == selected_label].iloc[0]
    home_team  = sel_row["_home"]
    away_team  = sel_row["_away"]
    match_id   = int(sel_row["match_id"])

    # Scores – guard against NaN (some postponed/walkover matches)
    def _safe_int(v, default=0) -> int:
        try:
            return int(v) if pd.notna(v) else default
        except (TypeError, ValueError):
            return default

    home_score = _safe_int(sel_row.get("home_score"))
    away_score = _safe_int(sel_row.get("away_score"))

    our_team      = st.radio("Analyse press for:", [home_team, away_team])
    opponent_team = away_team if our_team == home_team else home_team

# ── Load events ───────────────────────────────────────────────────────────────
try:
    ev = _cached_events(match_id)
except Exception as exc:
    st.error(f"Could not load events for match {match_id}: {exc}")
    st.stop()

# ── Constants ─────────────────────────────────────────────────────────────────
_SX = 105.0 / SB_PITCH_LEN   # 120 → 105
_SY = 68.0  / SB_PITCH_WID   # 80  → 68

_ON_TARGET  = {"Goal", "Saved"}
_SHOT_TYPES = {"Pressure", "Interception", "Tackle", "Ball Recovery"}


# ── Data-extraction helpers ───────────────────────────────────────────────────

def _safe_str(v, fallback: str = "Unknown") -> str:
    """Return string value, replacing NaN/None with fallback."""
    if isinstance(v, str):
        return v if v not in ("", "nan", "NaN") else fallback
    try:
        if pd.isna(v):
            return fallback
    except Exception:
        pass
    return str(v)


def _extract_shots(team: str, flip: bool = False) -> pd.DataFrame:
    """
    Return shot rows for *team* with derived columns:
      goal, on_target, xg (float, 0 if missing), x_plot, y_plot.

    Empty DataFrame returned when: ev is empty, no shot col, or no shots exist.
    """
    if ev.empty or "type_name" not in ev.columns:
        return pd.DataFrame()

    mask  = (ev["type_name"] == "Shot") & (ev["team_name"] == team)
    shots = ev[mask].copy()

    if shots.empty:
        return pd.DataFrame()

    # Flat StatsBomb columns (already parsed by press_engine._normalise_events)
    shots["xg"] = pd.to_numeric(
        shots.get("shot_statsbomb_xg", pd.Series(np.nan, index=shots.index)),
        errors="coerce",
    ).fillna(0.0)

    shots["outcome"] = shots.get(
        "shot_outcome", pd.Series("Unknown", index=shots.index)
    ).fillna("Unknown").astype(str)

    shots["goal"]      = shots["outcome"] == "Goal"
    shots["on_target"] = shots["outcome"].isin(_ON_TARGET)

    # Body part / technique (nice-to-have; might be absent on older cache)
    for col in ("shot_body_part", "shot_technique", "shot_type"):
        shots[col] = shots.get(col, pd.Series("", index=shots.index)).fillna("")

    # Player name is already a plain string in the StatsBomb flat export
    shots["player_name"] = (
        shots["player"].apply(lambda v: _safe_str(v))
        if "player" in shots.columns else "Unknown"
    )

    # Position may be NaN for some events
    shots["position"] = (
        shots["position"].fillna("Unknown")
        if "position" in shots.columns else "Unknown"
    )

    # Coordinates → pitch drawing space; drop rows missing coordinates
    shots = shots.dropna(subset=["x", "y"])
    if flip:
        shots["x_plot"] = 105.0 - shots["x"] * _SX
        shots["y_plot"] = 68.0  - shots["y"] * _SY
    else:
        shots["x_plot"] = shots["x"] * _SX
        shots["y_plot"] = shots["y"] * _SY

    return shots.reset_index(drop=True)


def _extract_press(team: str) -> pd.DataFrame:
    """
    Return defensive-action rows (Pressure/Interception/Tackle/Ball Recovery)
    for *team*.  Rows missing x or y are kept but flagged; callers decide
    whether to drop them for spatial charts.
    """
    if ev.empty or "type_name" not in ev.columns:
        return pd.DataFrame()

    mask     = ev["type_name"].isin(_SHOT_TYPES) & (ev["team_name"] == team)
    press_ev = ev[mask].copy()

    if press_ev.empty:
        return pd.DataFrame()

    press_ev["player_name"] = (
        press_ev["player"].apply(lambda v: _safe_str(v))
        if "player" in press_ev.columns else "Unknown"
    )
    press_ev["position"] = (
        press_ev["position"].fillna("Unknown")
        if "position" in press_ev.columns else "Unknown"
    )

    press_ev["has_xy"] = press_ev["x"].notna() & press_ev["y"].notna()

    # Pre-compute plot coords for rows that have them
    with_xy = press_ev["has_xy"]
    press_ev.loc[with_xy, "x_plot"] = press_ev.loc[with_xy, "x"] * _SX
    press_ev.loc[with_xy, "y_plot"] = press_ev.loc[with_xy, "y"] * _SY

    return press_ev.reset_index(drop=True)


def _approx_possession(team: str) -> float:
    """Approximate possession % from poss_team_name event counts."""
    if ev.empty or "poss_team_name" not in ev.columns:
        return 50.0
    denom = ev["poss_team_name"].isin([home_team, away_team]).sum()
    if denom == 0:
        return 50.0
    return round(float((ev["poss_team_name"] == team).sum() / denom * 100), 1)


# ── Extract for this match ────────────────────────────────────────────────────
home_shots = _extract_shots(home_team, flip=False)
away_shots = _extract_shots(away_team, flip=True)
press_ev   = _extract_press(our_team)

home_xg  = float(home_shots["xg"].sum()) if not home_shots.empty else 0.0
away_xg  = float(away_shots["xg"].sum()) if not away_shots.empty else 0.0
poss_h   = _approx_possession(home_team)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("⚽ Match Analysis")
_ct = COLORS["text"]
_cm = COLORS["muted"]
match_date = str(sel_row.get("match_date", ""))
st.markdown(
    f"<h3 style='color:{_ct};'>"
    f"<b>{home_team}</b> &nbsp; {home_score} – {away_score} &nbsp; <b>{away_team}</b>"
    f"</h3>"
    f"<span style='color:{_cm};font-size:.9rem;'>La Liga 2015/16 &nbsp;·&nbsp; {match_date}"
    f" &nbsp;·&nbsp; Analysing press: <b style='color:{_ct};'>{our_team}</b></span>",
    unsafe_allow_html=True,
)
st.divider()

# ── Top KPIs ─────────────────────────────────────────────────────────────────
_h = home_team[:14]
_a = away_team[:14]
kpi_row([
    kpi_card(f"{_h} xG",    f"{home_xg:.2f}",  sub=f"{home_score} goal(s)",    accent=COLORS["primary"]),
    kpi_card(f"{_a} xG",    f"{away_xg:.2f}",  sub=f"{away_score} goal(s)",    accent=COLORS["secondary"]),
    kpi_card(f"{_h} shots", len(home_shots),                                    accent=COLORS["warning"]),
    kpi_card(f"{_a} shots", len(away_shots),                                    accent=COLORS["warning"]),
    kpi_card("Possession",  f"{poss_h:.0f}%",  sub=f"{_h} / {100-poss_h:.0f}% {_a}",
             accent=COLORS["primary"]),
    kpi_card("Press events", len(press_ev),    sub=f"{our_team[:14]}",         accent=COLORS["success"]),
])
with st.columns([18, 1])[1]:
    info_popover(
        "**xG (Expected Goals)** - probability (0–1) that a shot becomes a goal, "
        "based on location, angle, and technique. Sums all shots for the match. "
        "<br><br>"
        "**Shots** - total shot attempts including blocked, off target, and goals. "
        "<br><br>"
        "**Possession** - approximated from StatsBomb possession-team event counts, "
        "not GPS or exact ball-tracking. "
        "<br><br>"
        "**Press events** - combined count of Pressures, Interceptions, Tackles, and "
        "Ball Recoveries for the analysed team."
    )
st.markdown("<br>", unsafe_allow_html=True)

tab_shot, tab_xg, tab_press = st.tabs(
    ["🗺️ Shot Map", "📈 xG Timeline", "🔥 Press Analysis"]
)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 - SHOT MAP
# ═══════════════════════════════════════════════════════════════════════════════
with tab_shot:
    section_header(
        "Shot Map", icon="🗺️",
        subtitle=f"Home ({home_team}) attacks right · Away ({away_team}) attacks left · bubble = xG",
        help_text=(
            "Each marker is one shot. **Bubble size = xG** (expected goals) - "
            "larger bubble means a higher-quality chance. "
            "<br><br>"
            "**★ Goal** · **● On Target (saved)** · **◆ Blocked/Post** · **✕ Off Target** "
            "<br><br>"
            "**xG** is a probability (0–1) that a shot results in a goal, based on location, "
            "angle, and shot type. A team finishing above their xG over-performed; below means "
            "they were unlucky or the goalkeeper made exceptional saves. "
            "<br><br>"
            "Home team always attacks toward the right goal; away team coordinates are flipped "
            "so both teams attack toward their own goal on the diagram."
        ),
    )

    # Team selector
    shot_team_choice = st.radio(
        "Show shots for:", [home_team, away_team, "Both teams"],
        horizontal=True, key="shot_team_radio",
    )

    if shot_team_choice == home_team:
        shots_to_show = [(home_shots, home_team, COLORS["primary"])]
    elif shot_team_choice == away_team:
        shots_to_show = [(away_shots, away_team, COLORS["secondary"])]
    else:
        shots_to_show = [
            (home_shots, home_team, COLORS["primary"]),
            (away_shots, away_team, COLORS["secondary"]),
        ]

    fig = draw_pitch()

    any_shots = False
    for shot_df, team_label, team_color in shots_to_show:
        if shot_df.empty:
            continue
        any_shots = True

        # Build per-outcome colour/symbol; use team colour + shape variations
        for outcome_mask, label_suffix, alpha, symbol in [
            (shot_df["goal"],                                     "Goal",       1.0,  "star"),
            (~shot_df["goal"] & shot_df["on_target"],             "On Target",  0.85, "circle"),
            (~shot_df["on_target"] & shot_df["outcome"].isin({"Blocked", "Post"}),
                                                                  "Blocked/Post", 0.65, "diamond"),
            (shot_df["outcome"].isin({"Off T", "Wayward"}),      "Off Target", 0.45, "x"),
        ]:
            sub = shot_df[outcome_mask]
            if sub.empty:
                continue

            hover = [
                f"<b>{r['player_name']}</b><br>"
                f"Team: {team_label}<br>"
                f"Min: {r.get('minute', '?')}<br>"
                f"xG: {r['xg']:.3f}<br>"
                f"Outcome: {r['outcome']}<br>"
                f"Technique: {r.get('shot_technique', '')}<br>"
                f"Body part: {r.get('shot_body_part', '')}"
                for _, r in sub.iterrows()
            ]
            sizes = (sub["xg"] * 35).clip(lower=10) + 7

            fig.add_trace(go.Scatter(
                x=sub["x_plot"], y=sub["y_plot"],
                mode="markers",
                name=f"{team_label} - {label_suffix}",
                marker=dict(
                    size=sizes, color=team_color,
                    symbol=symbol, opacity=alpha,
                    line=dict(width=1.5, color=COLORS["bg"]),
                ),
                text=hover,
                hovertemplate="%{text}<extra></extra>",
            ))

    if not any_shots:
        st.info("No shot data available for the selected team(s) in this match.")

    st.plotly_chart(fig, width='stretch')

    # Summary metrics + detail table
    for shot_df, team_label, _ in shots_to_show:
        if shot_df.empty:
            st.caption(f"{team_label}: no shots recorded.")
            continue

        n_g  = int(shot_df["goal"].sum())
        n_ot = int(shot_df["on_target"].sum())
        n_s  = len(shot_df)
        xg_t = shot_df["xg"].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"{team_label[:18]} - Shots",     n_s)
        c2.metric("Goals",                           n_g)
        c3.metric("On Target",                       n_ot)
        c4.metric("Total xG",                        f"{xg_t:.2f}")

        tbl_cols = ["player_name", "minute", "xg", "outcome", "shot_type",
                    "shot_technique", "shot_body_part"]
        tbl_cols = [c for c in tbl_cols if c in shot_df.columns]
        tbl = shot_df[tbl_cols].copy().sort_values("minute").reset_index(drop=True)
        tbl.columns = [c.replace("shot_", "").replace("_", " ").title()
                       for c in tbl_cols]
        tbl["Xg"] = tbl["Xg"].round(3) if "Xg" in tbl.columns else tbl.get("xg", "")
        st.dataframe(tbl, width='stretch', hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 - xG TIMELINE (both teams)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_xg:
    section_header(
        "xG Timeline", icon="📈",
        subtitle="Cumulative xG for both teams - divergence from actual goals = luck",
        help_text=(
            "The lines show cumulative xG building up shot by shot through the match. "
            "**Stars on the line = actual goals scored.** "
            "<br><br>"
            "If a team's xG line finishes **above** their goal count → they were **unlucky** "
            "(created good chances but didn't convert). "
            "<br>If their xG finishes **below** their goals → they **over-performed** "
            "(scored more than the quality of their chances suggested). "
            "<br><br>"
            "A steep xG climb with no matching star = the goalkeeper or woodwork denied them. "
            "A star well above the xG line = a clinical finish on a low-probability chance. "
            "<br><br>"
            "Dashed vertical lines = goals. The halftime marker (HT) is dotted."
        ),
    )

    info_box(
        "Each step = a shot. Stars = goals. "
        "If a team's xG line finishes above their actual goals, they were "
        "<b>unlucky</b>; if below, they <b>over-performed</b> their chances."
    )

    if home_shots.empty and away_shots.empty:
        st.info("No shot data recorded for this match.")
    else:
        fig = go.Figure()

        for shot_df, team_label, color in [
            (home_shots, home_team, COLORS["primary"]),
            (away_shots, away_team, COLORS["secondary"]),
        ]:
            if shot_df.empty:
                continue

            s = shot_df.sort_values("minute").copy()
            s["cum_xg"] = s["xg"].cumsum()

            # Guard: if minute column contains NaN, drop those rows
            s = s.dropna(subset=["minute"])

            fig.add_trace(go.Scatter(
                x=s["minute"], y=s["cum_xg"],
                mode="lines+markers",
                name=f"{team_label} xG",
                line=dict(color=color, width=2.5, shape="hv"),
                marker=dict(
                    size=(s["xg"] * 28 + 5).clip(lower=5),
                    color=color,
                    symbol=["star" if g else "circle" for g in s["goal"]],
                ),
                text=[
                    f"<b>{r['player_name']}</b><br>{team_label}<br>"
                    f"Min {r['minute']} · xG {r['xg']:.3f}<br>"
                    f"Outcome: {r['outcome']}"
                    for _, r in s.iterrows()
                ],
                hovertemplate="%{text}<extra></extra>",
            ))

            # Vertical line + annotation for each goal
            goals = s[s["goal"]].copy()
            for _, gr in goals.iterrows():
                fig.add_vline(
                    x=gr["minute"], line_dash="dash",
                    line_color=color, opacity=0.55,
                )
                fig.add_annotation(
                    x=gr["minute"], y=gr["cum_xg"],
                    text=f"⚽ {gr['player_name'][:18]}",
                    showarrow=True, arrowhead=2,
                    font=dict(color=color, size=9),
                    ax=25, ay=-30,
                )

        # Halftime marker
        fig.add_vline(x=45, line_dash="dot", line_color=COLORS["muted"], opacity=0.4)
        fig.add_annotation(x=45, y=0, text="HT", showarrow=False,
                           font=dict(color=COLORS["muted"], size=9), yanchor="bottom")

        # Extend x-axis gracefully if extra time exists
        max_min = 95
        if not home_shots.empty and not away_shots.empty:
            all_mins = pd.concat([home_shots["minute"], away_shots["minute"]]).dropna()
            if not all_mins.empty:
                max_min = max(95, int(all_mins.max()) + 3)
        elif not home_shots.empty:
            max_min = max(95, int(home_shots["minute"].dropna().max()) + 3)
        elif not away_shots.empty:
            max_min = max(95, int(away_shots["minute"].dropna().max()) + 3)

        fig = style_chart(
            fig, height=380,
            xaxis=dict(range=[0, max_min], title="Minute", gridcolor=COLORS["grid"]),
            yaxis=dict(title="Cumulative xG", gridcolor=COLORS["grid"]),
        )
        st.plotly_chart(fig, width='stretch')

        # Per-team xG vs goals summary
        st.markdown("#### xG vs Goals Summary")
        summary_rows = []
        for shot_df, team_label, actual_goals in [
            (home_shots, home_team, home_score),
            (away_shots, away_team, away_score),
        ]:
            total_xg = round(shot_df["xg"].sum(), 2) if not shot_df.empty else 0.0
            shots_n  = len(shot_df)
            goals_n  = int(shot_df["goal"].sum()) if not shot_df.empty else actual_goals
            ot_n     = int(shot_df["on_target"].sum()) if not shot_df.empty else 0
            diff     = round(goals_n - total_xg, 2)
            verdict  = "Over-performed" if diff > 0.3 else "Under-performed" if diff < -0.3 else "On-track"
            summary_rows.append({
                "Team":         team_label,
                "Shots":        shots_n,
                "On Target":    ot_n,
                "Goals":        goals_n,
                "xG":           total_xg,
                "Goals − xG":   f"{diff:+.2f}",
                "Verdict":      verdict,
            })
        st.dataframe(pd.DataFrame(summary_rows), width='stretch', hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 - PRESS ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
with tab_press:
    section_header(
        "Press Analysis", icon="🔥",
        subtitle=f"{our_team} - where and how the press worked",
        help_text=(
            "Shows the spatial distribution of defensive actions for the selected team in this match. "
            "Defensive actions include: **Pressures, Interceptions, Tackles, Ball Recoveries**. "
            "<br><br>"
            "**Location Map** - dots on the pitch showing where each defensive action happened. "
            "Clustering near the opponent's goal = high press; clustering near your own goal = deep block. "
            "<br><br>"
            "**Press by Pitch Third** - how many defensive actions occurred in each third. "
            "High percentage in the attacking third indicates an aggressive, high-press style. "
            "<br><br>"
            "**Territory Depth by Player** - average x-coordinate of each player's defensive actions. "
            "Higher value = that player presses further up the pitch. "
            "Useful for spotting which players are anchoring the press vs sitting deep. "
            "<br><br>"
            "**Caveats:** This is event-level data for one match. Pressures specifically include "
            "StatsBomb's unique 'closing-down' events, which are richer than just tackles/interceptions."
        ),
    )

    if press_ev.empty:
        st.info(f"No pressing/defensive action data found for {our_team} in this match.")
    else:
        # ── Counts per type ────────────────────────────────────────────────────
        type_counts = press_ev["type_name"].value_counts()
        n_press  = int(type_counts.get("Pressure",         0))
        n_int    = int(type_counts.get("Interception",     0))
        n_tack   = int(type_counts.get("Tackle",           0))
        n_recov  = int(type_counts.get("Ball Recovery",    0))
        n_total  = len(press_ev)

        # Possession context
        poss_ours = _approx_possession(our_team)

        kpi_row([
            kpi_card("Pressures",    n_press,              accent=COLORS["primary"]),
            kpi_card("Interceptions", n_int,               accent=COLORS["secondary"]),
            kpi_card("Tackles",      n_tack,               accent=COLORS["warning"]),
            kpi_card("Ball Recoveries", n_recov,           accent=COLORS["success"]),
            kpi_card("Total actions", n_total,             accent=COLORS["primary"]),
            kpi_card("Possession",   f"{poss_ours:.0f}%",  sub=f"{our_team[:14]}", accent=COLORS["muted"]),
        ])
        st.markdown("<br>", unsafe_allow_html=True)

        spatial = press_ev[press_ev["has_xy"]].copy()

        c1, c2 = st.columns(2)

        # ── Press locations on pitch ───────────────────────────────────────────
        with c1:
            section_header("Press Location Map", icon="📍",
                           subtitle="x = pitch depth (high = pressing high)")

            if spatial.empty:
                st.info("No coordinate data for press events.")
            else:
                fig_p = draw_pitch()

                # Colour by type
                type_colors = {
                    "Pressure":      COLORS["primary"],
                    "Interception":  COLORS["secondary"],
                    "Tackle":        COLORS["warning"],
                    "Ball Recovery": COLORS["success"],
                }
                for ttype, tcolor in type_colors.items():
                    sub = spatial[spatial["type_name"] == ttype]
                    if sub.empty:
                        continue
                    fig_p.add_trace(go.Scatter(
                        x=sub["x_plot"], y=sub["y_plot"],
                        mode="markers", name=ttype,
                        marker=dict(
                            size=7, color=tcolor, opacity=0.6,
                            line=dict(width=0.5, color=COLORS["bg"]),
                        ),
                        text=[
                            f"<b>{r['player_name']}</b><br>"
                            f"{r['type_name']} · Min {r.get('minute', '?')}<br>"
                            f"x={r['x']:.0f}m"
                            for _, r in sub.iterrows()
                        ],
                        hovertemplate="%{text}<extra></extra>",
                    ))
                st.plotly_chart(fig_p, width='stretch')

        # ── Press by pitch third ───────────────────────────────────────────────
        with c2:
            section_header("Press by Pitch Third", icon="📊",
                           subtitle="Defensive / Middle / Attacking third")

            if spatial.empty:
                st.info("No coordinate data.")
            else:
                # StatsBomb pitch is 120m; thirds are 0–40, 40–80, 80–120
                def _third(x: float) -> str:
                    if x < 40:
                        return "Defensive"
                    if x < 80:
                        return "Middle"
                    return "Attacking"

                spatial["third"] = spatial["x"].apply(_third)
                third_counts = (
                    spatial.groupby(["third", "type_name"])
                    .size().reset_index(name="count")
                )
                third_order = ["Defensive", "Middle", "Attacking"]
                third_total = spatial["third"].value_counts().reindex(third_order, fill_value=0)

                fig_t = go.Figure()
                for ttype, tcolor in type_colors.items():
                    sub = third_counts[third_counts["type_name"] == ttype]
                    if sub.empty:
                        continue
                    counts = [
                        int(sub[sub["third"] == t]["count"].sum()) if t in sub["third"].values else 0
                        for t in third_order
                    ]
                    fig_t.add_trace(go.Bar(
                        x=third_order, y=counts,
                        name=ttype, marker_color=tcolor, opacity=0.85,
                    ))

                fig_t = style_chart(fig_t, height=280, barmode="stack",
                                    yaxis=dict(title="Actions", gridcolor=COLORS["grid"]))
                fig_t.update_layout(title="Actions by Pitch Third")
                st.plotly_chart(fig_t, width='stretch')

                # Quick verdict on press style
                att_pct = third_total["Attacking"] / max(third_total.sum(), 1) * 100
                def_pct = third_total["Defensive"] / max(third_total.sum(), 1) * 100
                if att_pct >= 35:
                    verdict = f"High press - {att_pct:.0f}% of actions in the attacking third."
                elif def_pct >= 40:
                    verdict = f"Defensive block - {def_pct:.0f}% of actions in their own third."
                else:
                    verdict = "Balanced mid-press across the pitch."
                st.success(f"**Press style:** {verdict}")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Territory depth per player ─────────────────────────────────────────
        section_header("Territory Depth by Player", icon="🗺️",
                       subtitle="Average x of defensive actions (higher = pressing further up)")
        info_box(
            "x < 40m = own defensive third &nbsp;·&nbsp; "
            "x 40–80m = midfield &nbsp;·&nbsp; "
            "x > 80m = opponent's half (high press)."
        )

        if spatial.empty:
            st.info("No coordinate data for territory depth.")
        else:
            depth = (
                spatial.groupby("player_name")["x"]
                .agg(["mean", "count"])
                .reset_index()
                .rename(columns={"mean": "avg_x", "count": "n_actions"})
                .query("n_actions >= 2")         # filter noise (< 2 actions)
                .sort_values("avg_x", ascending=False)
                .head(20)
            )

            if depth.empty:
                st.info("Not enough per-player data (< 2 actions each).")
            else:
                bar_colors = [
                    COLORS["success"] if x >= 80 else
                    COLORS["primary"] if x >= 60 else
                    COLORS["warning"] if x >= 40 else
                    COLORS["danger"]
                    for x in depth["avg_x"]
                ]
                fig_d = go.Figure(go.Bar(
                    x=depth["avg_x"], y=depth["player_name"],
                    orientation="h",
                    marker_color=bar_colors, opacity=0.88,
                    text=[
                        f"{v:.0f}m ({n} actions)"
                        for v, n in zip(depth["avg_x"], depth["n_actions"])
                    ],
                    textposition="outside",
                    customdata=depth["n_actions"],
                ))
                fig_d.add_vline(x=40,  line_dash="dot",  line_color=COLORS["muted"],   opacity=0.5)
                fig_d.add_vline(x=60,  line_dash="dot",  line_color=COLORS["warning"],  opacity=0.6,
                                annotation_text="Opp. half", annotation_font_color=COLORS["warning"])
                fig_d.add_vline(x=80,  line_dash="dash", line_color=COLORS["success"],  opacity=0.7,
                                annotation_text="High press", annotation_font_color=COLORS["success"])
                fig_d = style_chart(
                    fig_d,
                    height=max(300, len(depth) * 28),
                    xaxis=dict(range=[0, 125], title="Avg x of defensive actions (m)",
                               gridcolor=COLORS["grid"]),
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig_d, width='stretch')

        # ── Player press breakdown table ───────────────────────────────────────
        section_header("Player Press Breakdown", icon="👤")
        player_tbl = (
            press_ev.groupby(["player_name", "position", "type_name"])
            .size().reset_index(name="count")
            .pivot_table(index=["player_name", "position"],
                         columns="type_name", values="count", fill_value=0)
            .reset_index()
        )
        # Ensure all type columns exist even if zero for this match
        for col in ("Pressure", "Interception", "Tackle", "Ball Recovery"):
            if col not in player_tbl.columns:
                player_tbl[col] = 0
        player_tbl["Total"] = player_tbl[
            [c for c in ("Pressure", "Interception", "Tackle", "Ball Recovery")
             if c in player_tbl.columns]
        ].sum(axis=1)
        player_tbl = player_tbl.sort_values("Total", ascending=False).reset_index(drop=True)
        st.dataframe(player_tbl, width='stretch', hide_index=True)
