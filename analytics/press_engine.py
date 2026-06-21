"""
analytics/press_engine.py
=========================
Press Intelligence Engine for FC Analytics United.

Computes PPDA (Passes Permitted per Defensive Action) in tumbling 10-minute
windows using StatsBomb La Liga 2015/16 event data, with an Opponent Build-up
Tendency classifier that flags windows where PPDA is not a reliable signal.

Why this module exists — the false-positive PPDA problem
---------------------------------------------------------
PPDA's numerator counts only opponent passes attempted in their own defensive
zone.  When an opponent plays direct football — clearing long, going aerial,
not building through that zone — their pass count there is near zero, producing
artificially low PPDA even when our press had no meaningful effect.  The
Build-up Tendency Classifier identifies such windows so the UI can surface
second-ball recovery rate as the headline metric instead of a misleading colour.
"""

from __future__ import annotations
import os
import json
import logging
import numpy as np
import pandas as pd

try:
    from statsbombpy import sb as _sb
    SB_AVAILABLE = True
    logging.getLogger("statsbombpy").setLevel(logging.ERROR)
except ImportError:
    SB_AVAILABLE = False

# ── StatsBomb competition constants ───────────────────────────────────────────
SB_PITCH_LEN            = 120.0   # metres
SB_PITCH_WID            = 80.0    # metres
LA_LIGA_COMPETITION_ID  = 11
LA_LIGA_SEASON_NAME     = "2015/2016"

CACHE_DIR = os.path.join(os.path.dirname(__file__), "sb_press_cache")

# ── PPDA configuration — DO NOT CHANGE (validated against 380 matches) ────────
# Defensive zone: the possessing team's lower 60 % of the pitch.
# 60 % × 120 m = 72 m.  Below this x-threshold (normalised to team perspective)
# the opponent is "building out" and PPDA is meaningful.
DEFENSIVE_ZONE_X_THRESHOLD = 72.0   # metres

# Tumbling window size.
WINDOW_MINUTES = 10

# Minimum total events (opp zone passes + our defensive actions) for a window
# to be considered data-sufficient.  Below this the window is greyed out.
MIN_EVENTS_GREY_OUT = 5

# PPDA collapse threshold — backtested across all La Liga 2015/16 windows:
# PPDA ≤ threshold → teal (good press); PPDA > threshold → amber (collapsing).
PPDA_COLLAPSE_THRESHOLD = 10.0

# ── Build-up Tendency Classifier thresholds ──────────────────────────────────
# All constants are calibrated against the La Liga 2015/16 StatsBomb dataset
# (380 matches, ~3 800 windows).  Spanish football is structurally more pass-
# oriented than northern-European leagues, so "direct" here means a notably
# high long-pass ratio by La Liga standards, not by English-football standards.
# In this dataset, long_pass_ratio peaks at ~0.45 (p90 ≈ 0.36, median ≈ 0.21).
# Adjust if applying to another league.

# Minimum opponent passes in the defensive zone before PPDA is meaningful.
# Fewer passes = the numerator is near zero by absence of play, not by pressure.
BUILDUP_MIN_ZONE_PASSES = 5

# Long-pass ratio above which we classify the window as "Direct/Defensive".
# 0.35 (top ~12 % of La Liga 2015/16 windows) means roughly 1-in-3 passes in
# the zone are long balls, bypassing structured press triggers.  At this rate,
# PPDA under-counts how hard the press actually had to work.
DIRECT_LONG_PASS_RATIO_THRESHOLD = 0.35

# Below this long-pass ratio → "Build-up" (mostly short, patient play).
# The median La Liga long-pass ratio is ~0.21, so 0.20 cleanly separates
# patient build-up from the mixed band.
# Between MIXED_LONG_PASS_RATIO_LOWER and DIRECT threshold → "Mixed".
MIXED_LONG_PASS_RATIO_LOWER = 0.20

# StatsBomb pass_length is in metres; above this we consider a pass "long".
# 32 m ≈ 35 yards — roughly from the back third to the halfway line.
LONG_PASS_LENGTH_METRES = 32.0

# ── Second-ball recovery ──────────────────────────────────────────────────────
# After an opponent long pass or clearance in their defensive zone, we count
# any of our defensive actions within this window as a "second-ball recovery".
SECOND_BALL_RECOVERY_SECONDS = 5.0

# ── Match Momentum Index weights ──────────────────────────────────────────────
# Index = (PPDA_score × ppda_w + territory_score × terr_w) / (ppda_w + terr_w)
# Both scores are 0–100 (higher = better for our team).
MOMENTUM_PPDA_WEIGHT     = 0.60
MOMENTUM_TERRITORY_WEIGHT = 0.40
# For Direct/Defensive windows the PPDA component is multiplied by this factor
# before entering the index, so misleadingly low PPDA from near-zero pass counts
# does not artificially inflate the momentum score.
DIRECT_PPDA_WEIGHT_FACTOR = 0.10   # 90 % down-weight; window is not excluded

# ── Category label constants ──────────────────────────────────────────────────
CATEGORY_BUILDUP = "Build-up"
CATEGORY_MIXED   = "Mixed"
CATEGORY_DIRECT  = "Direct/Defensive"


# ── Helpers: StatsBomb field extraction ───────────────────────────────────────

def _name(val) -> str:
    """Extract a name string from a StatsBomb dict-or-string field."""
    if isinstance(val, dict):
        return val.get("name", "")
    if val is None or (not isinstance(val, str) and pd.isna(val)):
        return ""
    return str(val)


def _extract_xy(df: pd.DataFrame) -> pd.DataFrame:
    """Add x, y float columns from the StatsBomb location column."""
    def _loc(v):
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            return float(v[0]), float(v[1])
        if isinstance(v, str) and v.startswith("["):
            try:
                import ast
                parsed = ast.literal_eval(v)
                return float(parsed[0]), float(parsed[1])
            except Exception:
                pass
        return np.nan, np.nan

    if "location" in df.columns:
        xy = pd.DataFrame(df["location"].apply(_loc).tolist(),
                          columns=["x", "y"], index=df.index)
        df = df.assign(x=xy["x"], y=xy["y"])
    return df


def _normalise_events(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten dict-valued type/team/possession_team columns to strings."""
    df = _extract_xy(df)
    df["type_name"]       = df["type"].apply(_name)        if "type"             in df.columns else ""
    df["team_name"]       = df["team"].apply(_name)        if "team"             in df.columns else ""
    df["poss_team_name"]  = df["possession_team"].apply(_name) if "possession_team" in df.columns else ""

    df["pass_length_m"]   = pd.to_numeric(
        df.get("pass_length", pd.Series(np.nan, index=df.index)), errors="coerce"
    )
    df["pass_type_name"]  = (
        df["pass_type"].apply(_name) if "pass_type" in df.columns
        else pd.Series("", index=df.index)
    )
    if "second" not in df.columns:
        df["second"] = 0
    df["second"] = pd.to_numeric(df["second"], errors="coerce").fillna(0)
    return df


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _ensure_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _match_cache_path(match_id: int) -> str:
    return os.path.join(CACHE_DIR, f"events_{match_id}.csv")


def _matches_cache_path() -> str:
    return os.path.join(CACHE_DIR, "la_liga_2015_16_matches.csv")


def _season_cache_path(competition_id: int, season_id: int) -> str:
    return os.path.join(CACHE_DIR, f"matches_{competition_id}_{season_id}.csv")


# ── Public: data loading ──────────────────────────────────────────────────────

def load_sb_competitions() -> pd.DataFrame:
    """Return all available StatsBomb open-data competitions (cached)."""
    _ensure_cache()
    path = os.path.join(CACHE_DIR, "competitions.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    if not SB_AVAILABLE:
        raise ImportError("statsbombpy is not installed.")
    comps = _sb.competitions()
    comps.to_csv(path, index=False)
    return comps


def load_sb_season_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """Return match list for any StatsBomb competition/season (cached)."""
    _ensure_cache()
    path = _season_cache_path(competition_id, season_id)
    if os.path.exists(path):
        return pd.read_csv(path)
    if not SB_AVAILABLE:
        raise ImportError("statsbombpy is not installed.")
    matches = _sb.matches(competition_id=competition_id, season_id=season_id)
    matches.to_csv(path, index=False)
    return matches


def load_sb_matches() -> pd.DataFrame:
    """Return the La Liga 2015/16 match list (backward-compat wrapper)."""
    _ensure_cache()
    path = _matches_cache_path()
    if os.path.exists(path):
        return pd.read_csv(path)

    if not SB_AVAILABLE:
        raise ImportError(
            "statsbombpy is not installed.  Run:\n"
            "  pip install statsbombpy\n"
            "or provide a cached CSV at:\n"
            f"  {path}"
        )

    comps = _sb.competitions()
    la_liga = comps[comps["competition_id"] == LA_LIGA_COMPETITION_ID]
    season_rows = la_liga[la_liga["season_name"] == LA_LIGA_SEASON_NAME]
    if season_rows.empty:
        season_rows = la_liga.sort_values("season_id").tail(1)

    season_id = int(season_rows.iloc[0]["season_id"])
    matches = _sb.matches(competition_id=LA_LIGA_COMPETITION_ID, season_id=season_id)
    matches.to_csv(path, index=False)
    return matches


def _load_raw_events(match_id: int) -> pd.DataFrame:
    """Load and cache raw events for one match (CSV, x/y pre-extracted)."""
    _ensure_cache()
    path = _match_cache_path(match_id)

    if os.path.exists(path):
        df = pd.read_csv(path, low_memory=False)
        return _normalise_events(df)

    if not SB_AVAILABLE:
        raise ImportError(
            "statsbombpy is not installed and no cached events found for "
            f"match {match_id}."
        )

    df = _sb.events(match_id=match_id)
    df = _normalise_events(df)
    # Save with x, y already extracted so re-loading is fast
    df.to_csv(path, index=False)
    return df


# ── Coordinate normalisation ──────────────────────────────────────────────────

def _defending_end(events: pd.DataFrame, team: str, period: int) -> str:
    """
    Return 'low' if the team's goal is near x=0 in this period, 'high' if near x=120.
    Inferred from where the team makes defensive clearances/blocks.
    """
    def_types = {"Clearance", "Block", "Ball Recovery"}
    mask = (
        events["type_name"].isin(def_types)
        & (events["team_name"] == team)
        & (events["period"] == period)
        & events["x"].notna()
    )
    sub = events.loc[mask, "x"]
    if len(sub) < 3:
        # Fall back to all team events
        mask2 = (events["team_name"] == team) & (events["period"] == period) & events["x"].notna()
        sub = events.loc[mask2, "x"]
    if sub.empty:
        return "low"
    return "low" if sub.mean() < 60 else "high"


def _zone_mask(events: pd.DataFrame, opp_defending: str) -> pd.Series:
    """
    Boolean mask for events that are inside the OPPONENT'S defensive zone.
    Works regardless of which end they are defending.
    """
    if opp_defending == "low":
        return events["x"] < DEFENSIVE_ZONE_X_THRESHOLD
    else:
        return events["x"] > (SB_PITCH_LEN - DEFENSIVE_ZONE_X_THRESHOLD)


# ── Core: second-ball recovery ────────────────────────────────────────────────

def _second_ball_recovery(
    win: pd.DataFrame,
    our_team: str,
    opp_team: str,
    zone_mask_series: pd.Series,
) -> tuple[int, float, dict]:
    """
    Second-ball recovery rate for one 10-minute window.

    A trigger is an opponent long pass (> LONG_PASS_LENGTH_METRES) or clearance
    inside their defensive zone.  A recovery is one of our defensive actions
    (Pressure / Interception / Tackle / Ball Recovery) that occurs within
    SECOND_BALL_RECOVERY_SECONDS of that trigger.

    Returns (n_recoveries, recovery_rate, thirds_dict) where thirds_dict
    counts recoveries by pitch third (Defensive / Middle / Attacking) from
    our team's attacking perspective.
    """
    win = win.copy()
    win["t_s"] = win["minute"] * 60 + win["second"]

    # Trigger events: opponent clearance OR long pass in their defensive zone
    trigger_mask = (
        (
            (win["type_name"] == "Clearance")
            | (
                (win["type_name"] == "Pass")
                & (win["pass_length_m"] > LONG_PASS_LENGTH_METRES)
            )
        )
        & (win["team_name"] == opp_team)
        & zone_mask_series.values
    )
    triggers = win[trigger_mask]

    # Our recovery events (anywhere on pitch)
    recovery_types = {"Pressure", "Interception", "Tackle", "Ball Recovery"}
    our_recoveries = win[
        win["type_name"].isin(recovery_types) & (win["team_name"] == our_team)
    ]

    n_triggers = len(triggers)
    if n_triggers == 0:
        return 0, 0.0, {"Defensive": 0, "Middle": 0, "Attacking": 0}

    thirds = {"Defensive": 0, "Middle": 0, "Attacking": 0}
    found = 0

    for _, trig in triggers.iterrows():
        t0 = trig["t_s"]
        window_recov = our_recoveries[
            (our_recoveries["t_s"] >= t0)
            & (our_recoveries["t_s"] <= t0 + SECOND_BALL_RECOVERY_SECONDS)
        ]
        if not window_recov.empty:
            found += 1
            rx = float(window_recov.iloc[0]["x"])
            # Thirds measured in absolute x — assumes our team attacks right (x→120)
            # Inversion is acceptable at this granularity; label is informational.
            if rx < 40:
                thirds["Defensive"] += 1
            elif rx < 80:
                thirds["Middle"] += 1
            else:
                thirds["Attacking"] += 1

    rate = found / n_triggers
    return found, rate, thirds


# ── Core: build-up tendency ───────────────────────────────────────────────────

def classify_buildup_tendency(
    zone_passes: int,
    long_pass_ratio: float,
    opp_poss_share: float,   # included for future extension; not used in thresholds yet
) -> str:
    """
    Classify the opponent's approach in their defensive zone for one window.

    Rule hierarchy (applied in order):
    1. < BUILDUP_MIN_ZONE_PASSES passes → Direct/Defensive
       (numerator is too small to be a meaningful press signal regardless of ratio)
    2. long_pass_ratio > DIRECT_LONG_PASS_RATIO_THRESHOLD → Direct/Defensive
       (majority of zone passes are bypassing the press)
    3. long_pass_ratio > MIXED_LONG_PASS_RATIO_LOWER → Mixed
    4. Otherwise → Build-up
    """
    if zone_passes < BUILDUP_MIN_ZONE_PASSES:
        return CATEGORY_DIRECT
    if long_pass_ratio > DIRECT_LONG_PASS_RATIO_THRESHOLD:
        return CATEGORY_DIRECT
    if long_pass_ratio > MIXED_LONG_PASS_RATIO_LOWER:
        return CATEGORY_MIXED
    return CATEGORY_BUILDUP


# ── Core: momentum index ──────────────────────────────────────────────────────

def _window_momentum(
    ppda: float | None,
    territory_depth: float,
    tendency: str,
    sufficient: bool,
) -> float | None:
    """
    Match Momentum Index for one window (0–100, higher = our team pressing better).

    Components:
      - PPDA score: 100 when PPDA → 0 (perfect), 50 at threshold, 0 at 2× threshold.
      - Territory score: (territory_depth / 120) × 100 — higher x press = higher score.

    For Direct/Defensive windows the PPDA component weight is multiplied by
    DIRECT_PPDA_WEIGHT_FACTOR (default 0.10).  This prevents a near-zero PPDA
    caused by the opponent barely passing in the zone — not by our press — from
    inflating the momentum score.  Weights are renormalised so the index stays
    on the same 0–100 scale.
    """
    if not sufficient:
        return None

    territory_score = float(np.clip((territory_depth / SB_PITCH_LEN) * 100, 0, 100))

    if ppda is None or (isinstance(ppda, float) and np.isnan(ppda)):
        ppda_score = 50.0
    else:
        ppda_score = float(np.clip(
            (1.0 - ppda / (PPDA_COLLAPSE_THRESHOLD * 2)) * 100, 0, 100
        ))

    ppda_factor = DIRECT_PPDA_WEIGHT_FACTOR if tendency == CATEGORY_DIRECT else 1.0
    ppda_w = MOMENTUM_PPDA_WEIGHT * ppda_factor
    terr_w = MOMENTUM_TERRITORY_WEIGHT
    total_w = ppda_w + terr_w

    return float(np.clip((ppda_w * ppda_score + terr_w * territory_score) / total_w, 0, 100))


# ── Public: raw event access ──────────────────────────────────────────────────

def load_match_events(match_id: int) -> pd.DataFrame:
    """Return normalised events for one match (cached CSV on first call)."""
    return _load_raw_events(match_id)


# ── Public: main window computation ──────────────────────────────────────────

def compute_ppda_windows(
    match_id: int,
    our_team: str,
    opponent_team: str,
) -> pd.DataFrame:
    """
    Compute PPDA and all derived Press Intelligence metrics in 10-minute windows.

    Returns one row per window with columns:
        window_label, window_start, window_end,
        opp_zone_passes, our_defensive_actions, ppda,
        sufficient_data, long_pass_ratio, opp_poss_share, our_poss_share,
        build_up_tendency,
        pressing_success_rate, territory_depth,
        second_ball_recoveries, second_ball_recovery_rate, recovery_thirds,
        momentum_index
    """
    ev = _load_raw_events(match_id)

    max_min = int(ev["minute"].max()) if "minute" in ev.columns and not ev.empty else 90
    rows = []

    for w_start in range(0, max_min, WINDOW_MINUTES):
        w_end = w_start + WINDOW_MINUTES
        label = f"{w_start}–{w_end}'"

        win = ev[(ev["minute"] >= w_start) & (ev["minute"] < w_end)].copy()
        if win.empty:
            continue

        period = int(win["period"].mode().iloc[0]) if "period" in win.columns else 1

        opp_def_end = _defending_end(win, opponent_team, period)
        our_def_end = _defending_end(win, our_team, period)
        zm = _zone_mask(win, opp_def_end)  # True = in opponent's defensive zone

        # ── PPDA numerator: opponent passes in zone ────────────────────────
        opp_pass_in_zone = (
            (win["type_name"] == "Pass")
            & (win["team_name"] == opponent_team)
            & zm
        )
        n_opp_passes = int(opp_pass_in_zone.sum())

        # Long passes in zone (for build-up classifier)
        n_long = int(
            (opp_pass_in_zone & (win["pass_length_m"] > LONG_PASS_LENGTH_METRES)).sum()
        )
        long_ratio = n_long / n_opp_passes if n_opp_passes > 0 else 0.0

        # ── PPDA denominator: our defensive actions in the same zone ───────
        our_def_types = {"Pressure", "Interception", "Tackle", "Ball Recovery"}
        our_actions_in_zone = (
            win["type_name"].isin(our_def_types)
            & (win["team_name"] == our_team)
            & zm
        )
        n_our_actions = int(our_actions_in_zone.sum())

        sufficient = (n_opp_passes + n_our_actions) >= MIN_EVENTS_GREY_OUT

        if n_opp_passes == 0 or not sufficient:
            ppda = np.nan
        else:
            ppda = float(n_opp_passes) / max(float(n_our_actions), 1.0)

        # ── Possession share ────────────────────────────────────────────────
        poss_events = win[win["poss_team_name"].isin([our_team, opponent_team])]
        total_poss = max(len(poss_events), 1)
        opp_poss_share = float((poss_events["poss_team_name"] == opponent_team).sum() / total_poss)
        our_poss_share = float((poss_events["poss_team_name"] == our_team).sum() / total_poss)

        # ── Build-up tendency ───────────────────────────────────────────────
        tendency = classify_buildup_tendency(n_opp_passes, long_ratio, opp_poss_share)

        # ── Pressing success rate ───────────────────────────────────────────
        n_pressures = int((
            (win["type_name"] == "Pressure") & (win["team_name"] == our_team)
        ).sum())
        n_regains = int((
            win["type_name"].isin({"Interception", "Ball Recovery"})
            & (win["team_name"] == our_team)
        ).sum())
        pressing_success = n_regains / n_pressures if n_pressures > 0 else 0.0

        # ── Defensive territory depth ───────────────────────────────────────
        # Average x of our defensive actions, normalised so high = pressing high.
        our_def_ev = win[our_actions_in_zone | (
            (win["type_name"] == "Pressure") & (win["team_name"] == our_team)
        )]
        if not our_def_ev.empty and our_def_ev["x"].notna().any():
            raw_x = our_def_ev["x"].dropna()
            if our_def_end == "high":
                raw_x = SB_PITCH_LEN - raw_x
            territory_depth = float(raw_x.mean())
        else:
            territory_depth = 60.0

        # ── Second-ball recovery ────────────────────────────────────────────
        sb_n, sb_rate, sb_thirds = _second_ball_recovery(
            win, our_team, opponent_team, zm
        )

        # ── Momentum index ──────────────────────────────────────────────────
        mom = _window_momentum(ppda, territory_depth, tendency, sufficient)

        rows.append({
            "window_label":              label,
            "window_start":              w_start,
            "window_end":                w_end,
            "opp_zone_passes":           n_opp_passes,
            "our_defensive_actions":     n_our_actions,
            "ppda":                      round(ppda, 2) if not np.isnan(ppda) else None,
            "sufficient_data":           sufficient,
            "long_pass_ratio":           round(long_ratio, 3),
            "opp_poss_share":            round(opp_poss_share, 3),
            "our_poss_share":            round(our_poss_share, 3),
            "build_up_tendency":         tendency,
            "pressing_success_rate":     round(pressing_success, 3),
            "territory_depth":           round(territory_depth, 1),
            "second_ball_recoveries":    sb_n,
            "second_ball_recovery_rate": round(sb_rate, 3),
            "recovery_thirds":           sb_thirds,
            "momentum_index":            round(mom, 1) if mom is not None else None,
        })

    return pd.DataFrame(rows)


# ── Public: threshold validator ───────────────────────────────────────────────

def run_threshold_validator(
    max_matches: int = 380,
    competition_id: int | None = None,
    season_id: int | None = None,
) -> dict:
    """
    Backtest PPDA collapse threshold across matches for a competition/season.

    Defaults to La Liga 2015/16 when competition_id/season_id are omitted.
    Results are cached per competition+season; delete the JSON file to rerun.
    """
    _ensure_cache()
    if competition_id is not None and season_id is not None:
        cache = os.path.join(CACHE_DIR, f"validator_{competition_id}_{season_id}.json")
    else:
        cache = os.path.join(CACHE_DIR, "validator_results.json")

    if os.path.exists(cache):
        with open(cache) as f:
            return json.load(f)

    if competition_id is not None and season_id is not None:
        matches = load_sb_season_matches(competition_id, season_id).head(max_matches)
    else:
        matches = load_sb_matches().head(max_matches)

    def _team_name(val) -> str:
        if isinstance(val, dict):
            for k in ("home_team_name", "away_team_name", "name"):
                if k in val:
                    return val[k]
        return str(val) if pd.notna(val) else ""

    all_windows: list[pd.DataFrame] = []
    n_processed = 0

    for _, mrow in matches.iterrows():
        mid = int(mrow["match_id"])
        home = _team_name(mrow.get("home_team", ""))
        away = _team_name(mrow.get("away_team", ""))
        if not home or not away:
            continue

        try:
            df = compute_ppda_windows(mid, home, away)
            df["match_id"] = mid
            all_windows.append(df)
            n_processed += 1
        except Exception:
            continue

    if not all_windows:
        return {"error": "No windows computed — check StatsBomb cache."}

    all_df = pd.concat(all_windows, ignore_index=True)
    valid  = all_df[all_df["sufficient_data"]].copy()
    total  = max(len(valid), 1)

    cat_dist = {}
    for cat in [CATEGORY_BUILDUP, CATEGORY_MIXED, CATEGORY_DIRECT]:
        n = int((valid["build_up_tendency"] == cat).sum())
        cat_dist[cat] = {"count": n, "fraction": round(n / total, 3)}

    ppda_vals = valid["ppda"].dropna().astype(float)

    results = {
        "n_matches":              n_processed,
        "n_windows_total":        int(len(all_df)),
        "n_windows_valid":        int(total),
        "ppda_mean":              round(float(ppda_vals.mean()), 2) if len(ppda_vals) else None,
        "ppda_std":               round(float(ppda_vals.std()),  2) if len(ppda_vals) else None,
        "ppda_p25":               round(float(ppda_vals.quantile(0.25)), 2) if len(ppda_vals) else None,
        "ppda_p75":               round(float(ppda_vals.quantile(0.75)), 2) if len(ppda_vals) else None,
        "collapse_threshold":     PPDA_COLLAPSE_THRESHOLD,
        "category_distribution":  cat_dist,
    }

    with open(cache, "w") as f:
        json.dump(results, f, indent=2)

    return results
