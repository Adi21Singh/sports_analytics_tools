"""
data/real_loader.py

Adapts the FBref 2025/26 players_data CSV into the 6 DataFrames used throughout
the analytics pages.  Real season totals (goals, shots, tackles, etc.) are
disaggregated into synthetic per-match records; physical/passing metrics that
FBref does not provide are drawn from position-specific profiles.

Returns the same tuple signature as data.generator.load_data():
    players, training, wellness, matches, match_players, events
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import POSITION_PROFILES, SESSION_FACTORS, PITCH_LEN, PITCH_WID

try:
    import streamlit as st
    _cache = st.cache_data
except ImportError:
    def _cache(fn):  # no-op when running outside Streamlit
        return fn

# ── Constants ─────────────────────────────────────────────────────────────────

CSV_PATH = "players_data-2025_2026.csv"

# 2025/26 Premier League season: 38 matchday Saturdays
_SEASON_START = datetime(2025, 8, 16)
_MATCH_DATES  = [_SEASON_START + timedelta(weeks=i) for i in range(38)]

# FBref Pos code → internal position key (matching config.POSITION_PROFILES)
_POS_MAP: dict[str, str] = {
    "GK":    "GK",
    "DF":    "CB",
    "DF,MF": "CB",
    "MF,DF": "CDM",
    "MF":    "CM",
    "MF,FW": "CAM",
    "FW,MF": "CAM",
    "FW":    "ST",
    "DF,FW": "LB",
}

# Prefer CDM → CDM key (config uses "CDM" not in keys above - map to closest)
# config.py has: GK, CB, LB, CDM, CM, CAM, LW, ST - CDM is "CDM"
_VALID_POSITIONS = set(POSITION_PROFILES.keys())


def _clean_pos(raw: str) -> str:
    raw = str(raw).strip()
    pos = _POS_MAP.get(raw, "CM")
    # Ensure it's a key that exists in POSITION_PROFILES
    if pos not in _VALID_POSITIONS:
        pos = "CM"
    return pos


def _rng(mean: float, std: float, lo: float = 0.0) -> float:
    return float(max(lo, np.random.normal(mean, std)))


def _rng_int(mean: float, std: float, lo: int = 0) -> int:
    return int(max(lo, round(np.random.normal(mean, std))))


def _compute_xg(shot_x: float, shot_y: float,
                is_header: bool = False, is_penalty: bool = False,
                under_pressure: bool = False) -> float:
    """Use the calibrated xG model from analytics.performance."""
    from analytics.performance import compute_xg
    return compute_xg(shot_x, shot_y, PITCH_LEN, PITCH_WID,
                      is_header=is_header, is_penalty=is_penalty,
                      under_pressure=under_pressure)


# ── Step 1: load and clean the raw CSV ────────────────────────────────────────

def _read_raw(csv_path) -> pd.DataFrame:
    import io
    if isinstance(csv_path, (bytes, bytearray)):
        return pd.read_csv(io.BytesIO(csv_path))
    return pd.read_csv(csv_path)


def _load_csv(csv_path) -> pd.DataFrame:
    df = _read_raw(csv_path)

    # The file has duplicated info blocks (keeper, shooting, misc sections).
    # Keep one row per Player+Squad combination (the first/main stats block).
    df = df.drop_duplicates(subset=["Player", "Squad"]).copy()

    # Numeric coercion for every column we use
    _nums = [
        "MP", "Starts", "Min", "90s", "Age",
        "Gls", "Ast", "Sh", "SoT", "TklW", "Int",
        "CrdY", "CrdR", "Fls", "Fld", "Crs",
        "G/Sh", "G/SoT", "Sh/90", "SoT%",
    ]
    for col in _nums:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Age may be stored as a float like 25.0
    df["Age"] = df["Age"].fillna(24).astype(int)

    # Only keep players with at least 1 appearance
    df = df[df["MP"] >= 1].reset_index(drop=True)
    return df


@_cache
def get_available_squads(csv_path=CSV_PATH) -> list[str]:
    """Return sorted list of team names available in the dataset."""
    df = _read_raw(csv_path)[["Squad"]]
    return sorted(df["Squad"].dropna().unique().tolist())


@_cache
def get_available_leagues(csv_path=CSV_PATH) -> list[str]:
    """Return sorted list of competition names in the dataset."""
    df = _read_raw(csv_path)[["Comp"]]
    return sorted(df["Comp"].dropna().unique().tolist())


# ── Step 2: build players DataFrame ───────────────────────────────────────────

def _build_players(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, row in enumerate(df.itertuples(index=False), start=1):
        rows.append({
            "id":       i,
            "name":     row.Player,
            "position": _clean_pos(row.Pos),
            "age":      int(row.Age),
            "number":   (i % 99) + 1,
            "squad":    row.Squad,
            "nation":   row.Nation if hasattr(row, "Nation") else "",
        })
    return pd.DataFrame(rows)


# ── Step 3: build match_players - disaggregate season totals ──────────────────

def _build_match_players(df: pd.DataFrame, players: pd.DataFrame, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    random.seed(seed)

    rows: list[dict] = []

    for _, pl in players.iterrows():
        raw   = df[df.index == (pl["id"] - 1)].iloc[0]  # same index as players build
        pos   = pl["position"]
        prof  = POSITION_PROFILES[pos]
        mp    = int(raw.get("MP", 1))
        if mp == 0:
            continue

        # Season totals from real data
        gls_total = int(raw.get("Gls",  0))
        ast_total = int(raw.get("Ast",  0))
        sh_total  = int(raw.get("Sh",   0))
        sot_total = int(raw.get("SoT",  0))
        tkl_total = int(raw.get("TklW", 0))
        int_total = int(raw.get("Int",  0))
        crd_y     = int(raw.get("CrdY", 0))
        min_total = float(raw.get("Min", mp * 70))

        # xG quality estimate (shots → xg conversion rate, capped at realistic range)
        g_per_sh  = float(raw.get("G/Sh", 0.0))
        xg_rate   = float(np.clip(g_per_sh if g_per_sh > 0 else 0.10, 0.04, 0.35))

        # Select mp match dates without replacement (or with replacement if > 38)
        match_dates = random.sample(_MATCH_DATES, min(mp, len(_MATCH_DATES)))
        if mp > len(_MATCH_DATES):
            extras = random.choices(_MATCH_DATES, k=mp - len(_MATCH_DATES))
            match_dates = sorted(match_dates + extras)

        # Distribute goals/assists/shots/tackles across matches (multinomial)
        def _distribute(total: int, n: int) -> list[int]:
            if total == 0:
                return [0] * n
            p = np.ones(n) / n
            return list(np.random.multinomial(total, p))

        gls_per  = _distribute(gls_total,  mp)
        ast_per  = _distribute(ast_total,  mp)
        sh_per   = _distribute(sh_total,   mp)
        sot_per  = _distribute(sot_total,  mp)
        tkl_per  = _distribute(tkl_total,  mp)
        int_per  = _distribute(int_total,  mp)

        avg_mins = min_total / mp

        for i, mdate in enumerate(match_dates):
            # Minutes this match (varied around avg, capped 10–90)
            mins = float(np.clip(np.random.normal(avg_mins, 10), 10, 90))
            frac = mins / 90.0

            def _m(key: str) -> float:
                mu, sigma = prof[key]
                return max(0.0, np.random.normal(mu * frac, sigma * 0.45))

            shots    = sh_per[i]
            goals    = min(gls_per[i], shots)
            assists  = ast_per[i]
            sot      = min(sot_per[i], shots)
            tkl_won  = tkl_per[i]
            interc   = int_per[i]

            # Physical metrics from position profile
            dist     = round(_m("distance_m"))
            hsr_m    = round(_m("hsr_m"))
            sprint_m = round(min(_m("sprint_m") * 0.85, hsr_m))
            spr_c    = max(0, round(_m("sprint_count")))
            accel    = max(0, round(_m("accel_count")))
            decel    = max(0, round(_m("decel_count")))
            spd      = round(float(np.random.normal(prof["max_speed_kmh"][0],
                                                    prof["max_speed_kmh"][1] * 0.4)), 1)

            # Passing (synthetic, position-based)
            passes   = max(5, round(_m("passes")))
            pass_pct = float(np.clip(np.random.normal(prof["pass_pct"][0],
                                                      prof["pass_pct"][1]), 0.45, 1.0))
            prog_p   = max(0, round(_m("progressive_passes")))
            key_p    = max(0, round(_m("key_passes")))

            # Dribbles
            drb_att = max(0, round(_m("dribbles_att")))
            drb_won = min(drb_att, max(0, round(_m("dribbles_won"))))

            # Aerial
            aer_att = max(0, round(_m("aerial_att")))
            aer_won = min(aer_att, max(0, round(_m("aerial_won"))))

            # Pressures
            press     = max(0, round(_m("pressures")))
            press_won = max(0, round(_m("pressure_won")))

            touches_b = max(0, round(_m("touches_box")))
            saves     = max(0, round(_m("saves"))) if pos == "GK" else 0

            # xG: real shots distributed, rate from actual G/Sh
            total_xg = sum(
                xg_rate * float(np.clip(np.random.normal(1, 0.3), 0.3, 2.0))
                for _ in range(shots)
            )
            xa = round(max(0.0, np.random.normal(
                prof["xa"][0] * frac, prof["xa"][1]
            )), 3)

            # Rating: base from profile, boosted for goals/assists
            rating_base = float(np.clip(
                np.random.normal(prof["match_rating"][0], prof["match_rating"][1]),
                4.5, 9.5
            ))
            rating = round(min(9.5, rating_base + goals * 0.4 + assists * 0.25), 1)

            rows.append({
                "match_id":               i + 1,
                "date":                   pd.Timestamp(mdate.date()),
                "player_id":              int(pl["id"]),
                "player_name":            pl["name"],
                "position":               pos,
                "starter":                mins > 45,
                "minutes_played":         round(mins),
                "distance_m":             dist,
                "hsr_m":                  hsr_m,
                "sprint_m":               sprint_m,
                "sprint_count":           spr_c,
                "accel_count":            accel,
                "decel_count":            decel,
                "max_speed_kmh":          spd,
                "work_rate":              round(dist / mins, 1) if mins else 0,
                "passes":                 passes,
                "pass_completion":        round(pass_pct, 3),
                "progressive_passes":     prog_p,
                "key_passes":             key_p,
                "shots":                  shots,
                "goals":                  goals,
                "assists":                assists,
                "xa":                     xa,
                "xg":                     round(total_xg, 3),
                "dribbles_attempted":     drb_att,
                "dribbles_won":           drb_won,
                "touches_in_box":         touches_b,
                "tackles_attempted":      tkl_won + max(0, round(_m("tackles_att")) - tkl_won),
                "tackles_won":            tkl_won,
                "interceptions":          interc,
                "aerial_duels_attempted": aer_att,
                "aerial_duels_won":       aer_won,
                "pressures":              press,
                "pressures_won":          press_won,
                "saves":                  saves,
                "match_rating":           rating,
            })

    mp_df = pd.DataFrame(rows)
    if not mp_df.empty:
        mp_df["date"] = pd.to_datetime(mp_df["date"])
    return mp_df


# ── Step 4: synthetic training sessions (same logic as generator) ─────────────

def _build_training(players: pd.DataFrame, seed: int) -> pd.DataFrame:
    from data.generator import build_training_sessions
    return build_training_sessions(players, seed)


# ── Step 5: synthetic wellness (same logic as generator) ─────────────────────

def _build_wellness(players: pd.DataFrame, training: pd.DataFrame, seed: int) -> pd.DataFrame:
    from data.generator import build_wellness
    return build_wellness(players, training, seed)


# ── Step 6: synthetic match results ──────────────────────────────────────────

def _build_matches(mp_df: pd.DataFrame, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    random.seed(seed)

    opponents = [
        "Arsenal", "Manchester City", "Liverpool", "Chelsea", "Tottenham",
        "Newcastle", "Aston Villa", "Brighton", "West Ham", "Wolves",
        "Everton", "Fulham", "Crystal Palace", "Brentford", "Bournemouth",
        "Nottingham Forest", "Burnley", "Sheffield Utd", "Luton Town", "Sunderland",
    ]

    rows = []
    for mid, mdate in enumerate(_MATCH_DATES[:38], start=1):
        # Derive goals_for from aggregated player goals that match day
        day_goals = (
            mp_df[mp_df["match_id"] == mid]["goals"].sum()
            if not mp_df.empty else 0
        )
        gf = int(day_goals) if day_goals > 0 else int(np.random.poisson(1.6))
        ga = int(np.random.poisson(1.3))
        result = "Win" if gf > ga else ("Draw" if gf == ga else "Loss")

        rows.append({
            "match_id":       mid,
            "date":           pd.Timestamp(mdate.date()),
            "opponent":       opponents[(mid - 1) % len(opponents)],
            "home_away":      "Home" if mid % 2 == 1 else "Away",
            "goals_for":      gf,
            "goals_against":  ga,
            "result":         result,
            "possession_pct": round(float(np.clip(np.random.normal(53, 6), 35, 70)), 1),
            "ppda":           round(float(np.clip(np.random.normal(9.5, 2.0), 4, 20)), 1),
        })
    return pd.DataFrame(rows)


# ── Step 7: shot events ───────────────────────────────────────────────────────

def _build_events(mp_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in mp_df.iterrows():
        for _ in range(int(row["shots"])):
            sx = float(np.random.uniform(78, PITCH_LEN))
            sy = float(np.random.uniform(14, 54))
            xg_val = _compute_xg(sx, sy)
            rows.append({
                "match_id":    row["match_id"],
                "date":        row["date"],
                "player_id":   row["player_id"],
                "player_name": row["player_name"],
                "position":    row["position"],
                "minute":      int(np.random.randint(1, max(2, int(row["minutes_played"])))),
                "x":           round(sx, 1),
                "y":           round(sy, 1),
                "xg":          round(xg_val, 3),
                "on_target":   bool(np.random.random() < 0.36),
                "goal":        bool(np.random.random() < xg_val * 0.9),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


# ── Public API ────────────────────────────────────────────────────────────────

def load_real_data(
    csv_path: str = CSV_PATH,
    squad_filter: str | None = None,
    seed: int = 42,
) -> tuple:
    """
    Load and adapt the FBref CSV.  Returns:
        (players, training, wellness, matches, match_players, events)

    squad_filter - if given, restrict to that team name (e.g. 'Arsenal').
    """
    raw = _load_csv(csv_path)

    if squad_filter:
        raw = raw[raw["Squad"] == squad_filter].reset_index(drop=True)
        if raw.empty:
            raise ValueError(f"No players found for '{squad_filter}'. "
                             "Check get_available_squads() for valid names.")

    players     = _build_players(raw)
    match_pl    = _build_match_players(raw, players, seed)
    training    = _build_training(players, seed)
    wellness    = _build_wellness(players, training, seed)
    matches     = _build_matches(match_pl, seed)
    events      = _build_events(match_pl)

    return players, training, wellness, matches, match_pl, events


# Apply Streamlit cache when inside the app
load_real_data = _cache(load_real_data)
