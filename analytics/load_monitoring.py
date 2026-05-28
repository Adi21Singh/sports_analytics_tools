"""Training load analytics: ACWR, PMC (CTL/ATL/TSB), monotony, strain."""

from __future__ import annotations
import numpy as np
import pandas as pd
from config import acwr_zone


def calculate_acwr(
    load: pd.Series,
    dates: pd.Series,
    acute_days: int = 7,
    chronic_days: int = 28,
) -> pd.DataFrame:
    """
    Compute Acute:Chronic Workload Ratio (Gabbett 2016).

    Returns a daily DataFrame with columns:
      date, daily_load, acute_load, chronic_load, acwr, risk_zone
    """
    df = pd.DataFrame({"date": pd.to_datetime(dates), "load": load})
    df = df.groupby("date")["load"].sum().reset_index()
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    daily = df.set_index("date")["load"].reindex(date_range, fill_value=0)

    acute   = daily.rolling(acute_days,   min_periods=1).mean()
    chronic = daily.rolling(chronic_days, min_periods=1).mean()
    ratio   = (acute / chronic.replace(0, np.nan)).fillna(0)

    result = pd.DataFrame({
        "date":         daily.index,
        "daily_load":   daily.values,
        "acute_load":   acute.values,
        "chronic_load": chronic.values,
        "acwr":         ratio.values,
    })
    result["risk_zone"] = result["acwr"].map(acwr_zone)
    return result


def calculate_pmc(
    load: pd.Series,
    dates: pd.Series,
    tau_ctl: int = 42,
    tau_atl: int = 7,
) -> pd.DataFrame:
    """
    Performance Management Chart (Banister 1991, adapted).

    Fitness (CTL) = 42-day EWMA of daily load
    Fatigue (ATL) =  7-day EWMA of daily load
    Form    (TSB) = CTL − ATL

    Zones:
      TSB  > +5     → Peaked / fresh
      TSB  -10 to 5 → Optimal
      TSB  -30 to -10 → Productive overreaching
      TSB  < -30    → Overtraining risk
    """
    df = pd.DataFrame({"date": pd.to_datetime(dates), "load": load})
    df = df.groupby("date")["load"].sum().reset_index()
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    daily = df.set_index("date")["load"].reindex(date_range, fill_value=0)

    ctl = daily.ewm(span=tau_ctl, adjust=False).mean()
    atl = daily.ewm(span=tau_atl, adjust=False).mean()
    tsb = ctl - atl

    return pd.DataFrame({
        "date":         daily.index,
        "daily_load":   daily.values,
        "ctl":          ctl.values.round(1),  # Fitness
        "atl":          atl.values.round(1),  # Fatigue
        "tsb":          tsb.values.round(1),  # Form
    })


def calculate_monotony_strain(
    load: pd.Series,
    dates: pd.Series,
    window: int = 7,
) -> pd.DataFrame:
    """
    Foster's training monotony and strain (Foster 1998).

    Monotony = weekly mean / weekly std
    Strain   = weekly mean × Monotony
    """
    df = pd.DataFrame({"date": pd.to_datetime(dates), "load": load})
    df = df.groupby("date")["load"].sum().reset_index()
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    daily = df.set_index("date")["load"].reindex(date_range, fill_value=np.nan)

    roll_mean = daily.rolling(window, min_periods=3).mean()
    roll_std  = daily.rolling(window, min_periods=3).std().replace(0, 0.01)
    monotony  = roll_mean / roll_std
    strain    = roll_mean * monotony

    return pd.DataFrame({
        "date":     daily.index,
        "daily":    daily.values,
        "mean":     roll_mean.values,
        "monotony": monotony.values,
        "strain":   strain.values,
    })


def availability_pct(
    training: pd.DataFrame,
    player_id: int,
    total_sessions_per_player: int | None = None,
) -> float:
    """Return percentage of scheduled sessions the player attended."""
    attended = len(training[training["player_id"] == player_id])
    if total_sessions_per_player is None:
        # Estimate from most-attended player
        total_sessions_per_player = training.groupby("player_id").size().max()
    return round(attended / total_sessions_per_player * 100, 1)
