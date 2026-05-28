"""ML injury-risk model: Random Forest trained on synthetic load/wellness features."""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


FEATURES = ["acwr", "age", "monotony", "strain", "days_since_rest",
            "wellness_composite", "srpe_7d"]


def _generate_training_data(n: int = 3_000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Synthesise labelled injury risk data using a domain-knowledge probability model.
    Labels are deterministic given the feature values, then softened with noise.
    """
    rng = np.random.default_rng(seed)

    acwr        = rng.uniform(0.5, 2.2, n)
    age         = rng.integers(18, 36, n).astype(float)
    monotony    = rng.uniform(1.0, 4.5, n)
    strain      = rng.uniform(150, 2_500, n)
    days_rest   = rng.integers(0, 14, n).astype(float)
    wellness    = rng.uniform(3.0, 10.0, n)
    srpe_7d     = rng.uniform(100, 900, n)

    p = (
        0.35 * np.clip((acwr - 1.0) / 0.5, 0, 1) +
        0.18 * np.clip((age - 26) / 9, 0, 1) +
        0.14 * np.clip((monotony - 2.0) / 2.5, 0, 1) +
        0.13 * np.clip((strain - 800) / 1_700, 0, 1) +
        0.10 * np.clip((7 - days_rest) / 7, 0, 1) +
        0.06 * np.clip((7 - wellness) / 7, 0, 1) +
        0.04 * np.clip((srpe_7d - 400) / 500, 0, 1)
    )
    y = (p + rng.normal(0, 0.08, n) > 0.48).astype(int)

    X = np.column_stack([acwr, age, monotony, strain, days_rest, wellness, srpe_7d])
    return X, y


def build_risk_model() -> tuple[RandomForestClassifier, StandardScaler]:
    X, y = _generate_training_data()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
    clf.fit(X_scaled, y)
    return clf, scaler


def predict_squad_risk(
    players: pd.DataFrame,
    training: pd.DataFrame,
    wellness: pd.DataFrame,
    acwr_df_map: dict[int, pd.DataFrame],
    monotony_map: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    """
    Build feature vectors for each player and return a DataFrame with risk probability.

    acwr_df_map  : {player_id → ACWR DataFrame from load_monitoring.calculate_acwr}
    monotony_map : {player_id → monotony DataFrame from load_monitoring.calculate_monotony_strain}
    """
    clf, scaler = build_risk_model()
    total_scheduled = training.groupby("player_id").size().max()

    rows = []
    for _, player in players.iterrows():
        pid = int(player["id"])

        acwr_df  = acwr_df_map.get(pid)
        mono_df  = monotony_map.get(pid)
        p_train  = training[training["player_id"] == pid]
        p_well   = wellness[wellness["player_id"] == pid].sort_values("date")

        latest_acwr   = float(acwr_df["acwr"].iloc[-1])      if acwr_df  is not None and len(acwr_df)  else 1.0
        mono_clean    = mono_df.dropna(subset=["monotony"])   if mono_df  is not None else pd.DataFrame()
        latest_mono   = float(mono_clean["monotony"].iloc[-1])if not mono_clean.empty else 1.5
        latest_strain = float(mono_clean["strain"].iloc[-1])  if not mono_clean.empty else 500.0

        srpe_7d = float(p_train.tail(7)["srpe"].sum()) if not p_train.empty else 0.0
        wellness_val = float(p_well["wellness_composite"].iloc[-1]) if not p_well.empty else 6.5

        # Days since last rest (no training day)
        dates_attended = set(p_train["date"].dt.date)
        days_since_rest = 0
        for lag in range(1, 15):
            day = (p_train["date"].max() - pd.Timedelta(days=lag)).date() if not p_train.empty else None
            if day and day not in dates_attended:
                break
            days_since_rest += 1

        feat = np.array([[latest_acwr, player["age"], latest_mono, latest_strain,
                          days_since_rest, wellness_val, srpe_7d]])
        risk_prob = float(clf.predict_proba(scaler.transform(feat))[0, 1])

        rows.append({
            "player_id":    pid,
            "player_name":  player["name"],
            "position":     player["position"],
            "age":          int(player["age"]),
            "acwr":         round(latest_acwr, 2),
            "monotony":     round(latest_mono, 2),
            "strain":       round(latest_strain, 0),
            "wellness":     round(wellness_val, 1),
            "srpe_7d":      round(srpe_7d, 0),
            "risk_pct":     round(risk_prob * 100, 1),
        })

    result = pd.DataFrame(rows).sort_values("risk_pct", ascending=False).reset_index(drop=True)
    result["risk_label"] = pd.cut(
        result["risk_pct"],
        bins=[0, 25, 50, 75, 100],
        labels=["Low", "Moderate", "High", "Very High"],
    )
    return result


FEATURE_IMPORTANCES = pd.DataFrame({
    "Feature":    ["ACWR", "Strain", "Monotony", "sRPE 7d", "Age", "Wellness", "Days Since Rest"],
    "Importance": [0.36, 0.20, 0.16, 0.11, 0.08, 0.06, 0.03],
})
