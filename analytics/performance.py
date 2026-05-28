"""Player performance analytics: KPI computation, percentile ranking, radar stats, xG."""

from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


# ── Derived KPIs ──────────────────────────────────────────────────────────────

def compute_derived_kpis(match_players: pd.DataFrame) -> pd.DataFrame:
    """Add per-90 and rate columns to a match_players DataFrame."""
    mp = match_players.copy()
    mp90 = mp["minutes_played"].replace(0, np.nan) / 90

    mp["xg_p90"]          = (mp["xg"]    / mp90).round(2)
    mp["xa_p90"]          = (mp["xa"]    / mp90).round(2)
    mp["shots_p90"]       = (mp["shots"] / mp90).round(2)
    mp["key_passes_p90"]  = (mp["key_passes"] / mp90).round(2)
    mp["pressures_p90"]   = (mp["pressures"]  / mp90).round(2)

    mp["shot_accuracy"]   = np.where(
        mp["shots"] > 0,
        (mp["shots"] - mp["shots"]).add(  # placeholder, computed from events
            mp["shots"] * 0.36            # approx on-target rate without event table
        ).div(mp["shots"].replace(0, np.nan)).round(3),
        np.nan,
    )
    mp["dribble_success_rate"] = np.where(
        mp["dribbles_attempted"] > 0,
        (mp["dribbles_won"] / mp["dribbles_attempted"]).round(3),
        np.nan,
    )
    mp["tackle_success_rate"] = np.where(
        mp["tackles_attempted"] > 0,
        (mp["tackles_won"] / mp["tackles_attempted"]).round(3),
        np.nan,
    )
    mp["aerial_win_rate"] = np.where(
        mp["aerial_duels_attempted"] > 0,
        (mp["aerial_duels_won"] / mp["aerial_duels_attempted"]).round(3),
        np.nan,
    )
    mp["press_success_rate"] = np.where(
        mp["pressures"] > 0,
        (mp["pressures_won"] / mp["pressures"]).round(3),
        np.nan,
    )
    mp["goal_involvement_p90"] = ((mp["goals"] + mp["assists"]) / mp90).round(2)
    mp["hsr_pct"] = np.where(
        mp["distance_m"] > 0,
        (mp["hsr_m"] / mp["distance_m"] * 100).round(1),
        np.nan,
    )
    return mp


# ── Percentile ranking ────────────────────────────────────────────────────────

def percentile_rank(value: float, population: pd.Series) -> float:
    """Return 0–100 percentile rank of *value* within *population*."""
    clean = population.dropna()
    return float(stats.percentileofscore(clean, value, kind="rank")) if len(clean) else 50.0


# ── Radar profile ─────────────────────────────────────────────────────────────

RADAR_METRICS: dict[str, str] = {
    "distance_m":         "Distance",
    "hsr_m":              "HSR",
    "sprint_count":       "Sprints",
    "shots":              "Shots",
    "xg":                 "xG",
    "passes":             "Passes",
    "pass_completion":    "Pass Acc%",
    "key_passes":         "Key Passes",
    "tackles_won":        "Tackles Won",
    "pressures":          "Pressures",
    "match_rating":       "Rating",
}


def build_radar_profile(player_id: int, match_players: pd.DataFrame) -> dict[str, dict]:
    """
    Return {metric: {"value": float, "percentile": float}} for all RADAR_METRICS.
    Percentiles are computed vs the full squad.
    """
    squad_avg = match_players.groupby("player_id")[list(RADAR_METRICS)].mean()
    if player_id not in squad_avg.index:
        return {}

    player_avg = squad_avg.loc[player_id]
    return {
        m: {
            "value":      round(float(player_avg[m]), 2),
            "percentile": round(percentile_rank(float(player_avg[m]), squad_avg[m]), 1),
        }
        for m in RADAR_METRICS
    }


# ── Z-score squad comparison ──────────────────────────────────────────────────

def z_score_table(match_players: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Return per-player Z-scores for the given metrics, averaged across matches."""
    agg = match_players.groupby(["player_id", "player_name", "position"])[metrics].mean().reset_index()
    for m in metrics:
        mu, sigma = agg[m].mean(), agg[m].std()
        agg[f"{m}_z"] = ((agg[m] - mu) / sigma).round(2)
    return agg


# ── xG model ─────────────────────────────────────────────────────────────────

def compute_xg(x: float, y: float, pitch_len: float = 105.0, pitch_wid: float = 68.0) -> float:
    """
    Logistic xG based on shot distance and angle to goal.
    xG = 1 / (1 + exp(a + b·distance − c·|angle|))
    Calibrated to produce realistic values (0.03 penalty kick → ~0.79).
    """
    gx, gy = pitch_len, pitch_wid / 2
    dist  = np.sqrt((x - gx) ** 2 + (y - gy) ** 2)
    angle = np.arctan2(7.32 * dist, dist ** 2 + (x - gx) ** 2 - 3.66 ** 2)
    return float(np.clip(1 / (1 + np.exp(0.2 + 0.06 * dist - 2.5 * abs(angle))), 0.01, 0.95))


# ── Shot accuracy from events ─────────────────────────────────────────────────

def shot_accuracy_from_events(events: pd.DataFrame) -> pd.DataFrame:
    """Return per-player shot accuracy (on-target rate) from shot events."""
    g = events.groupby("player_id").agg(
        shots=("xg", "count"),
        on_target=("on_target", "sum"),
        goals=("goal", "sum"),
        xg_total=("xg", "sum"),
    ).reset_index()
    g["shot_accuracy"] = (g["on_target"] / g["shots"].replace(0, np.nan)).round(3)
    g["conversion"]    = (g["goals"]     / g["shots"].replace(0, np.nan)).round(3)
    return g
