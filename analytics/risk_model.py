"""ML injury-risk model: Random Forest trained on synthetic load/wellness features.

Validation methodology note
----------------------------
The original model was trained and evaluated on the same synthetic dataset,
which is circular: the synthetic labels were generated using the same feature
relationships the model was asked to learn.

This revision:
  1. Uses a 70/30 stratified train/test split so reported metrics are on
     genuinely held-out data.
  2. Runs 5-fold stratified cross-validation on the training set.
  3. Reports AUC-ROC, precision, recall, F1, and Brier score.
  4. Derives feature importances from the fitted model (not hardcoded).
  5. Adds cross-validation std to quantify model stability.

Limitation: the underlying data is still synthetic, so metrics indicate
internal consistency rather than real-world predictive validity.  A
production model would require retrospective injury records from a real squad.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score,
    f1_score, brier_score_loss, confusion_matrix,
)


FEATURES = ["acwr", "age", "monotony", "strain", "days_since_rest",
            "wellness_composite", "srpe_7d"]


def _generate_training_data(n: int = 5_000, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """
    Synthesise labelled injury-risk data using a domain-knowledge probability
    model (coefficients follow published literature proportions).
    Labels use soft probabilistic assignment with Gaussian noise to prevent
    perfectly separable classes.

    NOTE: because labels are derived from the features, a model achieving
    very high AUC is not evidence of real predictive power — it reflects
    how well it has recovered the generating function.
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
    # Heavier noise to prevent over-separable synthetic classes
    y = (p + rng.normal(0, 0.12, n) > 0.48).astype(int)

    X = np.column_stack([acwr, age, monotony, strain, days_rest, wellness, srpe_7d])
    return X, y


def build_risk_model() -> tuple[RandomForestClassifier, StandardScaler, dict]:
    """
    Train the RF model and return (clf, scaler, metrics).

    metrics keys:
      test_auc, test_precision, test_recall, test_f1, test_brier,
      cv_auc_mean, cv_auc_std, cv_f1_mean, cv_f1_std,
      feature_importances (DataFrame), confusion_matrix (ndarray),
      n_train, n_test, class_balance_train
    """
    X, y = _generate_training_data()

    # ── Stratified train / test split ────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.30, stratify=y, random_state=42
    )

    scaler   = StandardScaler()
    Xtr_sc   = scaler.fit_transform(X_train)
    Xte_sc   = scaler.transform(X_test)

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=10,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    clf.fit(Xtr_sc, y_train)

    # ── Hold-out test metrics ─────────────────────────────────────────────────
    y_pred   = clf.predict(Xte_sc)
    y_prob   = clf.predict_proba(Xte_sc)[:, 1]

    test_metrics = {
        "test_auc":       round(float(roc_auc_score(y_test, y_prob)), 3),
        "test_precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 3),
        "test_recall":    round(float(recall_score(y_test, y_pred, zero_division=0)), 3),
        "test_f1":        round(float(f1_score(y_test, y_pred, zero_division=0)), 3),
        "test_brier":     round(float(brier_score_loss(y_test, y_prob)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "n_train":        int(len(y_train)),
        "n_test":         int(len(y_test)),
        "class_balance_train": round(float(y_train.mean()), 3),
    }

    # ── 5-fold stratified cross-validation on training set ────────────────────
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        clf, Xtr_sc, y_train, cv=cv,
        scoring=["roc_auc", "f1"],
        return_train_score=False,
    )
    test_metrics["cv_auc_mean"] = round(float(cv_results["test_roc_auc"].mean()), 3)
    test_metrics["cv_auc_std"]  = round(float(cv_results["test_roc_auc"].std()),  3)
    test_metrics["cv_f1_mean"]  = round(float(cv_results["test_f1"].mean()),       3)
    test_metrics["cv_f1_std"]   = round(float(cv_results["test_f1"].std()),        3)

    # ── Feature importances from fitted model (not hardcoded) ─────────────────
    fi = pd.DataFrame({
        "Feature":    FEATURES,
        "Importance": clf.feature_importances_.round(4),
    }).sort_values("Importance", ascending=False).reset_index(drop=True)
    fi["Feature"] = ["ACWR", "Age", "Monotony", "Strain",
                     "Days Since Rest", "Wellness", "sRPE 7d"][: len(fi)]
    # Re-sort by original order for display
    label_map = {
        "acwr": "ACWR", "age": "Age", "monotony": "Monotony",
        "strain": "Strain", "days_since_rest": "Days Since Rest",
        "wellness_composite": "Wellness", "srpe_7d": "sRPE 7d",
    }
    fi = pd.DataFrame({
        "Feature":    [label_map[f] for f in FEATURES],
        "Importance": clf.feature_importances_.round(4),
    }).sort_values("Importance", ascending=False).reset_index(drop=True)
    test_metrics["feature_importances"] = fi

    return clf, scaler, test_metrics


def predict_squad_risk(
    players: pd.DataFrame,
    training: pd.DataFrame,
    wellness: pd.DataFrame,
    acwr_df_map: dict[int, pd.DataFrame],
    monotony_map: dict[int, pd.DataFrame],
) -> tuple[pd.DataFrame, dict]:
    """
    Build feature vectors for each player and return (risk_df, model_metrics).

    acwr_df_map  : {player_id → ACWR DataFrame from load_monitoring.calculate_acwr}
    monotony_map : {player_id → monotony DataFrame from load_monitoring.calculate_monotony_strain}

    model_metrics contains AUC, precision, recall, F1, Brier, CV stats,
    feature importances, and confusion matrix from held-out test data.
    """
    clf, scaler, model_metrics = build_risk_model()

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

        srpe_7d      = float(p_train.tail(7)["srpe"].sum()) if not p_train.empty else 0.0
        wellness_val = float(p_well["wellness_composite"].iloc[-1]) if not p_well.empty else 6.5

        # Days since last rest (consecutive training days without a gap)
        dates_attended  = set(p_train["date"].dt.date)
        days_since_rest = 0
        if not p_train.empty:
            for lag in range(1, 15):
                day = (p_train["date"].max() - pd.Timedelta(days=lag)).date()
                if day not in dates_attended:
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
    return result, model_metrics


# ── Backward-compat shim: kept so pages that import FEATURE_IMPORTANCES still work.
# The real importances come from model_metrics["feature_importances"] at runtime.
FEATURE_IMPORTANCES = pd.DataFrame({
    "Feature":    ["ACWR", "Strain", "Monotony", "sRPE 7d", "Age", "Wellness", "Days Since Rest"],
    "Importance": [0.36, 0.20, 0.16, 0.11, 0.08, 0.06, 0.03],
})
