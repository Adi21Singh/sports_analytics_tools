"""Synthetic football data generator.

Produces realistic session, match, wellness and event data for a 25-player squad.
All tables are returned as DataFrames and cached via Streamlit when available.
"""

from __future__ import annotations
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import (
    POSITION_PROFILES, SESSION_FACTORS,
    PITCH_LEN, PITCH_WID,
    TEAM_NAME,
)

# ── Season window ─────────────────────────────────────────────────────────────
SEASON_START = datetime(2024, 8, 1)
SEASON_END   = datetime(2025, 2, 28)

# ── Squad ─────────────────────────────────────────────────────────────────────
SQUAD: list[dict] = [
    {"id":  1, "name": "James Kellerman",    "position": "GK",  "age": 29, "number":  1},
    {"id":  2, "name": "Marcus Webb",        "position": "GK",  "age": 24, "number": 13},
    {"id":  3, "name": "David Santos",       "position": "CB",  "age": 31, "number":  5},
    {"id":  4, "name": "Tom Hughes",         "position": "CB",  "age": 27, "number":  6},
    {"id":  5, "name": "Aaron Mitchell",     "position": "CB",  "age": 25, "number": 15},
    {"id":  6, "name": "Chris Blake",        "position": "CB",  "age": 23, "number": 22},
    {"id":  7, "name": "Luke Farrow",        "position": "LB",  "age": 26, "number":  3},
    {"id":  8, "name": "Ben Crawford",       "position": "LB",  "age": 22, "number": 17},
    {"id":  9, "name": "Kyle Turner",        "position": "RB",  "age": 28, "number":  2},
    {"id": 10, "name": "Trent Alderton",     "position": "RB",  "age": 25, "number": 21},
    {"id": 11, "name": "Jordan Hargreaves",  "position": "CDM", "age": 30, "number":  4},
    {"id": 12, "name": "Declan Ross",        "position": "CDM", "age": 27, "number":  8},
    {"id": 13, "name": "Kevin Dasilva",      "position": "CM",  "age": 32, "number": 10},
    {"id": 14, "name": "Jack Griffiths",     "position": "CM",  "age": 24, "number": 16},
    {"id": 15, "name": "Ross Baines",        "position": "CM",  "age": 26, "number":  7},
    {"id": 16, "name": "Emil Martinez",      "position": "CM",  "age": 22, "number": 28},
    {"id": 17, "name": "Martin Olsen",       "position": "CAM", "age": 29, "number": 11},
    {"id": 18, "name": "Bruno Ferreira",     "position": "CAM", "age": 26, "number": 20},
    {"id": 19, "name": "Sadio Mensah",       "position": "LW",  "age": 30, "number": 25},
    {"id": 20, "name": "Jack Rowe",          "position": "LW",  "age": 21, "number": 23},
    {"id": 21, "name": "Mo Sharif",          "position": "RW",  "age": 28, "number": 19},
    {"id": 22, "name": "Bukayo Sterling",    "position": "RW",  "age": 23, "number": 14},
    {"id": 23, "name": "Harry Kane-Wilson",  "position": "ST",  "age": 30, "number":  9},
    {"id": 24, "name": "Erling Jensen",      "position": "ST",  "age": 23, "number": 18},
    {"id": 25, "name": "Marcus Rashford-Cole","position":"ST",  "age": 25, "number": 27},
]

OPPONENTS = [
    "City FC","Arsenal United","Riverside Blues","Chelsea Town","Tottenham Athletic",
    "Leicester City","Everton FC","Brighton FC","West Ham Wanderers","Wolves FC",
    "Aston Villa","Newcastle Utd","Southampton FC","Crystal Palace","Fulham FC",
    "Brentford City","Bournemouth FC","Luton Town","Burnley FC","Sheffield Utd",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _rng_norm(mean: float, std: float, low: float = 0.0) -> float:
    return float(max(low, np.random.normal(mean, std)))

def _rng_int(mean: float, std: float, low: int = 0) -> int:
    return int(max(low, round(np.random.normal(mean, std))))

def _scale(profile_key: str, pos: str, factor: float, std_factor: float = 0.45) -> float:
    mu, sigma = POSITION_PROFILES[pos][profile_key]
    return _rng_norm(mu * factor, sigma * std_factor)


# ── Players ───────────────────────────────────────────────────────────────────

def build_players() -> pd.DataFrame:
    return pd.DataFrame(SQUAD)


# ── Training sessions ─────────────────────────────────────────────────────────

def _week_schedule(week_start: datetime) -> list[tuple[datetime, str]]:
    days = [
        (week_start,                "MD+1"),
        (week_start + timedelta(2), "MD-3"),
        (week_start + timedelta(3), "MD-2"),
        (week_start + timedelta(4), "MD-1"),
        (week_start + timedelta(6), "MD"),
    ]
    if random.random() < 0.4:
        days.append((week_start + timedelta(1), "GYM"))
    return days


def build_training_sessions(players: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed); random.seed(seed)
    rows = []
    week = SEASON_START

    while week <= SEASON_END:
        for date, stype in _week_schedule(week):
            if date > SEASON_END:
                continue
            sf = SESSION_FACTORS[stype]
            for _, player in players.iterrows():
                pos = player["position"]
                p   = POSITION_PROFILES[pos]
                # ~6% absence probability (slightly higher for older players)
                if random.random() < 0.06 + (player["age"] > 28) * 0.02:
                    continue

                d   = sf["d"]
                hi  = sf["hi"]
                dist    = round(_scale("distance_m", pos, d))
                hsr_m   = round(_scale("hsr_m",      pos, hi))
                spr_m   = round(min(_scale("sprint_m",  pos, hi * 0.85), hsr_m))
                spr_c   = _rng_int(*[v * d for v in p["sprint_count"]])
                accel   = _rng_int(*[v * d for v in p["accel_count"]])
                decel   = _rng_int(*[v * d for v in p["decel_count"]])
                spd     = _rng_norm(*p["max_speed_kmh"])
                pl      = round(_scale("player_load", pos, sf["pl"]), 1)
                rpe     = float(np.clip(np.random.normal(sf["rpe"], 0.8), 1, 10))
                dur     = max(20, int(np.random.normal(sf["dur"], 4)))
                hml     = round(spr_m + accel * 1.2 + decel * 1.0, 0)

                rows.append({
                    "player_id":       int(player["id"]),
                    "player_name":     player["name"],
                    "position":        pos,
                    "date":            pd.Timestamp(date.date()),
                    "session_type":    stype,
                    "duration_min":    dur,
                    "distance_m":      dist,
                    "hsr_m":           hsr_m,
                    "sprint_m":        spr_m,
                    "sprint_count":    spr_c,
                    "accel_count":     accel,
                    "decel_count":     decel,
                    "max_speed_kmh":   round(spd, 1),
                    "player_load":     pl,
                    "hml_m":           int(hml),
                    "rpe":             round(rpe, 1),
                    "srpe":            round(rpe * dur, 1),  # Foster sRPE
                    "work_rate":       round(dist / dur, 1) if dur else 0,
                })
        week += timedelta(7)

    df = pd.DataFrame(rows).sort_values(["player_id", "date"]).reset_index(drop=True)
    return df


# ── Wellness (daily subjective ratings) ───────────────────────────────────────

def build_wellness(players: pd.DataFrame, training: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Generate daily wellness scores correlated with prior-day training load."""
    np.random.seed(seed)
    rows = []
    date_range = pd.date_range(SEASON_START, SEASON_END, freq="D")

    # Build a quick lookup: player_id → date → srpe
    load_map = (
        training.groupby(["player_id", "date"])["srpe"].sum()
        .to_dict()
    )

    for _, player in players.iterrows():
        pid = int(player["id"])
        for date in date_range:
            prev = date - pd.Timedelta(days=1)
            prior_load = load_map.get((pid, prev), 0)
            fatigue_base = min(10, 4.0 + prior_load / 120)
            soreness_base = min(10, 3.5 + prior_load / 130)

            sleep   = float(np.clip(np.random.normal(7.0, 1.0), 3, 10))
            fatigue = float(np.clip(np.random.normal(fatigue_base, 1.0), 1, 10))
            soreness= float(np.clip(np.random.normal(soreness_base, 1.0), 1, 10))
            mood    = float(np.clip(np.random.normal(7.5 - fatigue * 0.3, 0.8), 2, 10))
            stress  = float(np.clip(np.random.normal(4.0, 1.2), 1, 10))

            # Composite: higher = better readiness (inverts fatigue/soreness/stress)
            composite = round(
                (sleep + (10 - fatigue) + (10 - soreness) + mood + (10 - stress)) / 5, 1
            )
            rows.append({
                "player_id":    pid,
                "player_name":  player["name"],
                "date":         date,
                "sleep_score":  round(sleep, 1),
                "fatigue_score":round(fatigue, 1),
                "soreness_score":round(soreness, 1),
                "mood_score":   round(mood, 1),
                "stress_score": round(stress, 1),
                "wellness_composite": composite,
            })
    return pd.DataFrame(rows)


# ── Matches ───────────────────────────────────────────────────────────────────

def build_matches(players: pd.DataFrame, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (matches, match_players, shot_events)."""
    np.random.seed(seed); random.seed(seed)
    n_matches = 20
    opps = random.sample(OPPONENTS, n_matches)
    match_start = SEASON_START + timedelta(days=7)

    match_rows, player_rows, event_rows = [], [], []

    for mid in range(1, n_matches + 1):
        mdate    = match_start + timedelta(weeks=mid - 1)
        opponent = opps[mid - 1]
        home_away= "Home" if mid % 2 == 1 else "Away"
        gf = int(np.random.poisson(1.6))
        ga = int(np.random.poisson(1.3))
        result = "Win" if gf > ga else ("Draw" if gf == ga else "Loss")
        poss   = float(np.clip(np.random.normal(52, 5), 38, 68))
        ppda   = float(np.clip(np.random.normal(9.5, 2.0), 4, 20))  # pressing metric

        match_rows.append({
            "match_id":      mid,
            "date":          pd.Timestamp(mdate.date()),
            "opponent":      opponent,
            "home_away":     home_away,
            "goals_for":     gf,
            "goals_against": ga,
            "result":        result,
            "possession_pct":round(poss, 1),
            "ppda":          round(ppda, 1),
        })

        gks  = players[players["position"] == "GK"]
        outf = players[players["position"] != "GK"]
        starting_gk  = gks.sample(1, random_state=mid).iloc[0]
        starters_out = outf.sample(min(10, len(outf)), random_state=mid)
        subs_pool    = outf.drop(starters_out.index).sample(
            min(9, len(outf) - len(starters_out)), random_state=mid + 500
        )

        lineup = pd.concat([gks.loc[[starting_gk.name]], starters_out])
        for _, pl in lineup.iterrows():
            _append_match_player(player_rows, event_rows, pl, mid, mdate, True, gf)

        for i, (_, pl) in enumerate(subs_pool.iterrows()):
            if i < 5 and random.random() < 0.6:
                _append_match_player(player_rows, event_rows, pl, mid, mdate, False, gf)

    matches_df = pd.DataFrame(match_rows)
    mp_df      = pd.DataFrame(player_rows)
    mp_df["date"] = pd.to_datetime(mp_df["date"])
    events_df  = pd.DataFrame(event_rows)
    if not events_df.empty:
        events_df["date"] = pd.to_datetime(events_df["date"])
    return matches_df, mp_df, events_df


def _append_match_player(
    player_rows: list, event_rows: list,
    player, mid: int, mdate: datetime, starter: bool, gf: int,
) -> None:
    pos = player["position"]
    p   = POSITION_PROFILES[pos]
    mins = int(np.random.randint(60, 91)) if starter else int(np.random.randint(10, 40))
    frac = mins / 90

    def _m(key: str) -> float:
        mu, sigma = p[key]
        return max(0.0, np.random.normal(mu * frac, sigma * 0.45))

    passes   = max(5, round(_m("passes")))
    pass_pct = float(np.clip(np.random.normal(p["pass_pct"][0], p["pass_pct"][1]), 0.45, 1.0))
    shots    = max(0, round(_m("shots")))
    goals    = min(round(_m("goals")), shots, gf)
    assists  = max(0, round(_m("assists")))
    drb_att  = max(0, round(_m("dribbles_att")))
    drb_won  = min(drb_att, max(0, round(_m("dribbles_won"))))
    tkl_att  = max(0, round(_m("tackles_att")))
    tkl_won  = min(tkl_att, max(0, round(_m("tackles_won"))))
    aer_att  = max(0, round(_m("aerial_att")))
    aer_won  = min(aer_att, max(0, round(_m("aerial_won"))))
    xa       = round(max(0, np.random.normal(p["xa"][0] * frac, p["xa"][1])), 3)
    prog_p   = max(0, round(_m("progressive_passes")))
    press    = max(0, round(_m("pressures")))
    press_won= max(0, round(_m("pressure_won")))
    touches_b= max(0, round(_m("touches_box")))
    key_p    = max(0, round(_m("key_passes")))
    saves    = max(0, round(_m("saves")))
    interc   = max(0, round(_m("interceptions")))
    rating   = float(np.clip(np.random.normal(p["match_rating"][0], p["match_rating"][1]), 4.5, 9.5))

    player_rows.append({
        "match_id":          mid,
        "date":              mdate.date(),
        "player_id":         int(player["id"]),
        "player_name":       player["name"],
        "position":          pos,
        "starter":           starter,
        "minutes_played":    mins,
        "distance_m":        round(_m("distance_m")),
        "hsr_m":             round(_m("hsr_m")),
        "sprint_m":          round(_m("sprint_m") * 0.85),
        "sprint_count":      max(0, round(_m("sprint_count"))),
        "accel_count":       max(0, round(_m("accel_count"))),
        "decel_count":       max(0, round(_m("decel_count"))),
        "max_speed_kmh":     round(float(np.random.normal(p["max_speed_kmh"][0], p["max_speed_kmh"][1] * 0.4)), 1),
        "work_rate":         round(_m("distance_m") / mins, 1) if mins else 0,
        "passes":            passes,
        "pass_completion":   round(pass_pct, 3),
        "progressive_passes":prog_p,
        "key_passes":        key_p,
        "shots":             shots,
        "goals":             goals,
        "assists":           assists,
        "xa":                xa,
        "xg":                0.0,  # computed below per shot event
        "dribbles_attempted":drb_att,
        "dribbles_won":      drb_won,
        "touches_in_box":    touches_b,
        "tackles_attempted": tkl_att,
        "tackles_won":       tkl_won,
        "interceptions":     interc,
        "aerial_duels_attempted": aer_att,
        "aerial_duels_won":  aer_won,
        "pressures":         press,
        "pressures_won":     press_won,
        "saves":             saves,
        "match_rating":      round(rating, 1),
    })

    # Generate shot events for this player in this match
    total_xg = 0.0
    for _ in range(shots):
        sx = float(np.random.uniform(78, 105))
        sy = float(np.random.uniform(14, 54))
        xg_val = _compute_xg(sx, sy)
        on_target = random.random() < 0.36
        is_goal   = random.random() < xg_val * 0.9
        total_xg += xg_val
        event_rows.append({
            "match_id":    mid,
            "date":        mdate.date(),
            "player_id":   int(player["id"]),
            "player_name": player["name"],
            "position":    pos,
            "minute":      int(np.random.randint(1, mins + 1)),
            "x":           round(sx, 1),
            "y":           round(sy, 1),
            "xg":          round(xg_val, 3),
            "on_target":   on_target,
            "goal":        is_goal,
        })

    # Patch xg total back into the player row
    if player_rows:
        player_rows[-1]["xg"] = round(total_xg, 3)


def _compute_xg(shot_x: float, shot_y: float) -> float:
    goal_x, goal_y = PITCH_LEN, PITCH_WID / 2
    dist  = np.sqrt((shot_x - goal_x) ** 2 + (shot_y - goal_y) ** 2)
    angle = np.arctan2(7.32 * dist, dist ** 2 + (shot_x - goal_x) ** 2 - 3.66 ** 2)
    return float(np.clip(1 / (1 + np.exp(0.2 + 0.06 * dist - 2.5 * abs(angle))), 0.01, 0.95))


# ── Cached loader ─────────────────────────────────────────────────────────────

def load_data(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (players, training, wellness, matches, match_players, events)."""
    players  = build_players()
    training = build_training_sessions(players, seed)
    wellness = build_wellness(players, training, seed)
    matches, match_players, events = build_matches(players, seed)
    return players, training, wellness, matches, match_players, events


# Wrap with Streamlit cache when running inside the app
try:
    import streamlit as st
    load_data = st.cache_data(load_data)
except ImportError:
    pass
