"""
xG model validation against StatsBomb open data.
=================================================
Downloads real shot events from StatsBomb's free open-data repository
(La Liga 2004-2020 seasons) and benchmarks two versions of our xG model:

  v1 (baseline) : distance + angle only         (original model)
  v2 (enhanced) : distance + angle + body part  (this revision)

Metrics computed against StatsBomb's own calibrated xG values:
  - Mean Squared Error (MSE)
  - Mean Absolute Error (MAE)
  - Log-loss (cross-entropy)
  - Brier score
  - Pearson correlation with StatsBomb xG
  - Calibration: mean predicted vs mean actual goal rate

StatsBomb pitch coordinates: x ∈ [0, 120], y ∈ [0, 80]
Our model coordinates:        x ∈ [0, 105], y ∈ [0, 68]
→ Scale factor applied: x * (105/120), y * (68/80)

Usage
-----
  python analytics/validate_xg.py

Results are printed to stdout and saved to:
  analytics/xg_validation_results.csv
"""

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss, brier_score_loss, mean_squared_error, mean_absolute_error
from scipy.stats import pearsonr

# ── Try to import statsbombpy ─────────────────────────────────────────────────
try:
    from statsbombpy import sb
    SB_AVAILABLE = True
except ImportError:
    SB_AVAILABLE = False

from analytics.performance import compute_xg


# ── Coordinate scaling ────────────────────────────────────────────────────────
SB_PITCH_LEN = 120.0
SB_PITCH_WID = 80.0
OUR_PITCH_LEN = 105.0
OUR_PITCH_WID = 68.0

def scale_coords(x_sb: float, y_sb: float) -> tuple[float, float]:
    """Convert StatsBomb coordinates to our model's coordinate system."""
    return x_sb * (OUR_PITCH_LEN / SB_PITCH_LEN), y_sb * (OUR_PITCH_WID / SB_PITCH_WID)


# ── Our v1 model (original - distance + angle only) ───────────────────────────
def xg_v1(x: float, y: float) -> float:
    """Original model: distance and angle, no body-part adjustment."""
    gx, gy = OUR_PITCH_LEN, OUR_PITCH_WID / 2
    dist   = np.sqrt((x - gx) ** 2 + (y - gy) ** 2)
    angle  = np.arctan2(7.32 * dist, dist ** 2 + (x - gx) ** 2 - 3.66 ** 2)
    return float(np.clip(1 / (1 + np.exp(0.2 + 0.06 * dist - 2.5 * abs(angle))), 0.01, 0.95))


# ── Our v2 model (enhanced) ───────────────────────────────────────────────────
def xg_v2(x: float, y: float, is_header: bool, is_penalty: bool,
          under_pressure: bool) -> float:
    return compute_xg(x, y, OUR_PITCH_LEN, OUR_PITCH_WID,
                      is_header=is_header, is_penalty=is_penalty,
                      under_pressure=under_pressure)


# ── Metrics helper ────────────────────────────────────────────────────────────
def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                    sb_xg: np.ndarray, label: str) -> dict:
    y_pred_clipped = np.clip(y_pred, 1e-6, 1 - 1e-6)
    corr_goal,  _ = pearsonr(y_pred, y_true)
    corr_sb,    _ = pearsonr(y_pred, sb_xg)
    return {
        "model":           label,
        "n_shots":         len(y_true),
        "n_goals":         int(y_true.sum()),
        "goal_rate":       round(float(y_true.mean()), 4),
        "mean_pred_xg":    round(float(y_pred.mean()), 4),
        "mse_vs_goals":    round(float(mean_squared_error(y_true, y_pred)), 5),
        "mae_vs_goals":    round(float(mean_absolute_error(y_true, y_pred)), 5),
        "log_loss":        round(float(log_loss(y_true, y_pred_clipped)), 5),
        "brier_score":     round(float(brier_score_loss(y_true, y_pred)), 5),
        "corr_with_goals": round(float(corr_goal), 4),
        "corr_with_sb_xg": round(float(corr_sb), 4),
        "mse_vs_sb_xg":    round(float(mean_squared_error(sb_xg, y_pred)), 5),
        "calibration_ratio": round(float(y_pred.mean() / max(y_true.mean(), 1e-9)), 4),
    }


# ── Load StatsBomb data ───────────────────────────────────────────────────────
def load_statsbomb_shots(max_matches: int = 200) -> pd.DataFrame:
    """
    Load shot events from StatsBomb open-data La Liga competitions.
    Uses statsbombpy library (pip install statsbombpy).
    Falls back to cached CSV if the library is unavailable.
    """
    cache_path = os.path.join(os.path.dirname(__file__), "sb_shots_cache.csv")

    # ── Check for cached data first ───────────────────────────────────────────
    if os.path.exists(cache_path):
        print(f"  Loading cached StatsBomb shots from {cache_path}")
        return pd.read_csv(cache_path)

    if not SB_AVAILABLE:
        raise ImportError(
            "statsbombpy not installed. Run:\n"
            "  pip install statsbombpy --break-system-packages\n"
            "or provide a cached sb_shots_cache.csv in the analytics/ folder."
        )

    print("  Fetching StatsBomb competition list...")
    comps = sb.competitions()

    # La Liga free competitions (comp_id=11)
    la_liga = comps[comps["competition_id"] == 11].sort_values("season_id")
    print(f"  Found {len(la_liga)} La Liga seasons in free tier")

    all_shots = []
    matches_loaded = 0

    for _, season_row in la_liga.iterrows():
        if matches_loaded >= max_matches:
            break
        comp_id   = int(season_row["competition_id"])
        season_id = int(season_row["season_id"])

        try:
            season_matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception:
            continue

        for _, match_row in season_matches.iterrows():
            if matches_loaded >= max_matches:
                break
            match_id = int(match_row["match_id"])
            try:
                events = sb.events(match_id=match_id)
                shots  = events[events["type"] == "Shot"].copy()
                if shots.empty:
                    continue

                # Extract fields we need
                records = []
                for _, s in shots.iterrows():
                    loc = s.get("location", [None, None])
                    if not isinstance(loc, (list, tuple)) or len(loc) < 2:
                        continue

                    body_part = ""
                    if isinstance(s.get("shot_body_part"), dict):
                        body_part = s["shot_body_part"].get("name", "")
                    elif isinstance(s.get("shot_body_part"), str):
                        body_part = s["shot_body_part"]

                    shot_type = ""
                    if isinstance(s.get("shot_type"), dict):
                        shot_type = s["shot_type"].get("name", "")
                    elif isinstance(s.get("shot_type"), str):
                        shot_type = s["shot_type"]

                    outcome = ""
                    if isinstance(s.get("shot_outcome"), dict):
                        outcome = s["shot_outcome"].get("name", "")
                    elif isinstance(s.get("shot_outcome"), str):
                        outcome = s["shot_outcome"]

                    records.append({
                        "x_sb":           float(loc[0]),
                        "y_sb":           float(loc[1]),
                        "sb_xg":          float(s.get("shot_statsbomb_xg", 0) or 0),
                        "goal":           int(outcome == "Goal"),
                        "body_part":      body_part,
                        "shot_type":      shot_type,
                        "under_pressure": bool(s.get("under_pressure", False)),
                    })

                if records:
                    all_shots.extend(records)
                    matches_loaded += 1

            except Exception:
                continue

        print(f"    Season {season_row.get('season_name','?')}: loaded {matches_loaded} matches so far")

    if not all_shots:
        raise ValueError("No shots loaded from StatsBomb data.")

    df = pd.DataFrame(all_shots)
    df.to_csv(cache_path, index=False)
    print(f"  Cached {len(df)} shots to {cache_path}")
    return df


# ── Main validation ───────────────────────────────────────────────────────────
def run_validation(max_matches: int = 200) -> pd.DataFrame:
    print("\n══════════════════════════════════════════")
    print("  StatsBomb xG Validation")
    print("══════════════════════════════════════════\n")

    print("Step 1: Loading StatsBomb shot data...")
    shots_df = load_statsbomb_shots(max_matches=max_matches)
    print(f"  Loaded {len(shots_df):,} shots "
          f"({int(shots_df['goal'].sum()):,} goals, "
          f"base rate {shots_df['goal'].mean():.3f})\n")

    # Scale coordinates to our system
    shots_df[["x", "y"]] = shots_df.apply(
        lambda r: pd.Series(scale_coords(r["x_sb"], r["y_sb"])), axis=1
    )
    shots_df["is_header"]  = shots_df["body_part"].str.contains("Head", case=False, na=False)
    shots_df["is_penalty"] = shots_df["shot_type"].str.contains("Penalty", case=False, na=False)

    y_true = shots_df["goal"].values.astype(float)
    sb_xg  = shots_df["sb_xg"].values

    print("Step 2: Running xG models...")
    shots_df["xg_v1"] = shots_df.apply(lambda r: xg_v1(r["x"], r["y"]), axis=1)
    shots_df["xg_v2"] = shots_df.apply(
        lambda r: xg_v2(r["x"], r["y"], r["is_header"],
                         r["is_penalty"], r["under_pressure"]), axis=1
    )

    # StatsBomb's own model as upper-bound reference
    sb_clipped = np.clip(sb_xg, 1e-6, 1 - 1e-6)

    results = []
    results.append(compute_metrics(y_true, shots_df["xg_v1"].values, sb_xg, "v1 (distance+angle only)"))
    results.append(compute_metrics(y_true, shots_df["xg_v2"].values, sb_xg, "v2 (+ body part + pressure)"))
    results.append(compute_metrics(y_true, sb_clipped,               sb_xg, "StatsBomb reference model"))

    results_df = pd.DataFrame(results)

    print("\nStep 3: Results\n")
    print(results_df.to_string(index=False))

    # ── Per-body-part breakdown for v2 ───────────────────────────────────────
    print("\n\nBreakdown by shot type (v2 model):")
    for label, mask in [
        ("Open-play foot", ~shots_df["is_header"] & ~shots_df["is_penalty"]),
        ("Headers",         shots_df["is_header"]),
        ("Penalties",       shots_df["is_penalty"]),
    ]:
        sub = shots_df[mask]
        if len(sub) < 10:
            continue
        yt = sub["goal"].values.astype(float)
        yp = sub["xg_v2"].values
        ll = log_loss(yt, np.clip(yp, 1e-6, 1 - 1e-6))
        print(f"  {label:25s}  n={len(sub):5,}  goals={int(yt.sum()):4,}  "
              f"base={yt.mean():.3f}  mean_pred={yp.mean():.3f}  log-loss={ll:.4f}")

    # ── Calibration summary ───────────────────────────────────────────────────
    print("\nCalibration check (mean predicted xG vs actual goal rate):")
    print(f"  v1: predicted {shots_df['xg_v1'].mean():.4f}  actual {y_true.mean():.4f}  "
          f"ratio {shots_df['xg_v1'].mean()/max(y_true.mean(),1e-9):.3f}")
    print(f"  v2: predicted {shots_df['xg_v2'].mean():.4f}  actual {y_true.mean():.4f}  "
          f"ratio {shots_df['xg_v2'].mean()/max(y_true.mean(),1e-9):.3f}")
    print(f"  SB: predicted {sb_xg.mean():.4f}  actual {y_true.mean():.4f}  "
          f"ratio {sb_xg.mean()/max(y_true.mean(),1e-9):.3f}")

    # Save
    out_path = os.path.join(os.path.dirname(__file__), "xg_validation_results.csv")
    results_df.to_csv(out_path, index=False)
    print(f"\nResults saved to {out_path}")

    return results_df


if __name__ == "__main__":
    run_validation(max_matches=200)
