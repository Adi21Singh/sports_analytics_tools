"""Central configuration - colors, thresholds, position profiles, chart defaults."""

from __future__ import annotations

# ── Team ──────────────────────────────────────────────────────────────────────
TEAM_NAME   = "La Liga"
SEASON      = "2015/16"
PITCH_LEN   = 105.0  # metres
PITCH_WID   = 68.0

# ── Design tokens ────────────────────────────────────────────────────────────
COLORS = {
    # backgrounds
    "bg":           "#0e1117",
    "surface":      "#1c1f26",
    "surface_alt":  "#23272f",
    "border":       "#2d3240",
    # accents
    "primary":      "#00c7a8",   # teal
    "secondary":    "#7c83fd",   # indigo
    "warning":      "#f59e0b",   # amber
    "danger":       "#ef4444",   # red
    "success":      "#22c55e",   # green
    # text
    "text":         "#f1f3f9",
    "muted":        "#9ca3af",
    # chart
    "grid":         "#2d3240",
}

PALETTE = ["#00c7a8", "#7c83fd", "#f59e0b", "#ef4444", "#22c55e",
           "#f472b6", "#38bdf8", "#fb923c", "#a3e635", "#e879f9"]

# ── Chart defaults (passed to update_layout) ─────────────────────────────────
CHART_BASE = dict(
    paper_bgcolor = COLORS["bg"],
    plot_bgcolor  = COLORS["surface"],
    font          = dict(color=COLORS["text"], size=12),
    margin        = dict(t=50, b=30, l=30, r=30),
    legend        = dict(orientation="h", y=1.08, bgcolor="rgba(0,0,0,0)"),
    xaxis         = dict(gridcolor=COLORS["grid"], zeroline=False),
    yaxis         = dict(gridcolor=COLORS["grid"], zeroline=False),
)

# ── Thresholds ────────────────────────────────────────────────────────────────
ACWR_ZONES = {           # (lo, hi, colour, label)
    "Under-training": (0.00, 0.80, COLORS["secondary"], "Under-training"),
    "Optimal":        (0.80, 1.30, COLORS["success"],   "Optimal"),
    "Caution":        (1.30, 1.50, COLORS["warning"],   "Caution"),
    "High Risk":      (1.50, 9.99, COLORS["danger"],    "High Risk"),
}

WELLNESS_LABELS = {
    "sleep_score":    "Sleep Quality",
    "fatigue_score":  "Fatigue (inv.)",
    "soreness_score": "Soreness (inv.)",
    "mood_score":     "Mood",
    "stress_score":   "Stress (inv.)",
}

# Wellness composite weights - McLean et al. (2010), Hooper & Mackinnon (1995)
# Sleep quality and subjective fatigue are the strongest predictors of next-day
# performance and injury risk.  Equal weighting (0.2 each) was the original
# error - replaced with evidence-based differential weighting.
WELLNESS_WEIGHTS = {
    "sleep_score":    0.30,   # inverted: higher sleep = higher readiness
    "fatigue_score":  0.30,   # inverted: lower fatigue = higher readiness
    "soreness_score": 0.20,   # inverted: lower soreness = higher readiness
    "mood_score":     0.10,   # direct: higher mood = higher readiness
    "stress_score":   0.10,   # inverted: lower stress = higher readiness
}

# ── Position profiles ─────────────────────────────────────────────────────────
# Each key maps to a dict of (mean, std) per metric for a match (~90 min).
# Scaling factors per session_type are applied in the generator.
POSITION_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "GK": {
        "distance_m":       (5_800, 400),  "hsr_m":         (200, 80),
        "sprint_m":         (80,  30),     "sprint_count":  (8,   3),
        "accel_count":      (12,  4),      "decel_count":   (10,  3),
        "max_speed_kmh":    (27.5, 1.2),   "player_load":   (280, 40),
        "passes":           (35, 8),       "pass_pct":      (0.78, 0.05),
        "progressive_passes":(5, 3),       "shots":         (0.0, 0.0),
        "xa":               (0.0, 0.0),    "goals":         (0.0, 0.0),
        "assists":          (0.0, 0.0),    "dribbles_att":  (0,   0),
        "dribbles_won":     (0,   0),      "key_passes":    (0,   0),
        "pressures":        (5,   3),      "pressure_won":  (2,   2),
        "tackles_att":      (1,   1),      "tackles_won":   (1,   1),
        "interceptions":    (0,   1),      "aerial_att":    (4,   2),
        "aerial_won":       (3,   2),      "touches_box":   (0,   0),
        "saves":            (4,   3),      "match_rating":  (6.8, 0.6),
    },
    "CB": {
        "distance_m":       (10_200, 600), "hsr_m":         (800, 200),
        "sprint_m":         (300, 100),    "sprint_count":  (18,  6),
        "accel_count":      (25,  7),      "decel_count":   (22,  6),
        "max_speed_kmh":    (30.5, 1.8),   "player_load":   (380, 50),
        "passes":           (65, 12),      "pass_pct":      (0.88, 0.04),
        "progressive_passes":(10, 5),      "shots":         (0.8, 0.8),
        "xa":               (0.05, 0.1),   "goals":         (0.1, 0.3),
        "assists":          (0.1, 0.3),    "dribbles_att":  (1,   1),
        "dribbles_won":     (0,   1),      "key_passes":    (0.5, 0.5),
        "pressures":        (12,  5),      "pressure_won":  (4,   3),
        "tackles_att":      (4,   2),      "tackles_won":   (3,   2),
        "interceptions":    (3,   2),      "aerial_att":    (6,   3),
        "aerial_won":       (4,   2),      "touches_box":   (1,   1),
        "saves":            (0,   0),      "match_rating":  (6.8, 0.6),
    },
    "LB": {
        "distance_m":       (11_500, 700), "hsr_m":         (1_100, 250),
        "sprint_m":         (450, 120),    "sprint_count":  (26,  8),
        "accel_count":      (30,  8),      "decel_count":   (26,  7),
        "max_speed_kmh":    (31.0, 1.8),   "player_load":   (420, 55),
        "passes":           (60, 10),      "pass_pct":      (0.85, 0.04),
        "progressive_passes":(14, 5),      "shots":         (0.5, 0.7),
        "xa":               (0.1, 0.15),   "goals":         (0.05, 0.2),
        "assists":          (0.2, 0.4),    "dribbles_att":  (2,   1),
        "dribbles_won":     (1,   1),      "key_passes":    (1.0, 0.8),
        "pressures":        (15,  6),      "pressure_won":  (5,   3),
        "tackles_att":      (3,   2),      "tackles_won":   (2,   1),
        "interceptions":    (2,   1),      "aerial_att":    (3,   2),
        "aerial_won":       (2,   1),      "touches_box":   (2,   2),
        "saves":            (0,   0),      "match_rating":  (6.8, 0.6),
    },
    "CDM": {
        "distance_m":       (11_000, 650), "hsr_m":         (950, 220),
        "sprint_m":         (380, 110),    "sprint_count":  (22,  7),
        "accel_count":      (28,  8),      "decel_count":   (24,  7),
        "max_speed_kmh":    (30.0, 1.6),   "player_load":   (400, 50),
        "passes":           (75, 12),      "pass_pct":      (0.87, 0.04),
        "progressive_passes":(18, 6),      "shots":         (0.8, 0.7),
        "xa":               (0.08, 0.12),  "goals":         (0.1, 0.3),
        "assists":          (0.2, 0.4),    "dribbles_att":  (2,   1),
        "dribbles_won":     (1,   1),      "key_passes":    (1.0, 0.8),
        "pressures":        (20,  7),      "pressure_won":  (7,   4),
        "tackles_att":      (5,   2),      "tackles_won":   (4,   2),
        "interceptions":    (4,   2),      "aerial_att":    (4,   2),
        "aerial_won":       (2,   2),      "touches_box":   (2,   2),
        "saves":            (0,   0),      "match_rating":  (6.9, 0.6),
    },
    "CM": {
        "distance_m":       (11_500, 700), "hsr_m":         (1_000, 250),
        "sprint_m":         (400, 120),    "sprint_count":  (24,  8),
        "accel_count":      (30,  8),      "decel_count":   (26,  7),
        "max_speed_kmh":    (30.5, 1.7),   "player_load":   (410, 55),
        "passes":           (80, 12),      "pass_pct":      (0.86, 0.04),
        "progressive_passes":(20, 7),      "shots":         (1.5, 1.0),
        "xa":               (0.12, 0.18),  "goals":         (0.2, 0.4),
        "assists":          (0.4, 0.5),    "dribbles_att":  (3,   1),
        "dribbles_won":     (2,   1),      "key_passes":    (2.0, 1.0),
        "pressures":        (18,  7),      "pressure_won":  (6,   4),
        "tackles_att":      (3,   2),      "tackles_won":   (2,   1),
        "interceptions":    (3,   2),      "aerial_att":    (2,   2),
        "aerial_won":       (1,   1),      "touches_box":   (3,   2),
        "saves":            (0,   0),      "match_rating":  (7.0, 0.6),
    },
    "CAM": {
        "distance_m":       (10_800, 650), "hsr_m":         (1_050, 250),
        "sprint_m":         (420, 120),    "sprint_count":  (25,  8),
        "accel_count":      (31,  8),      "decel_count":   (27,  7),
        "max_speed_kmh":    (31.5, 1.8),   "player_load":   (400, 50),
        "passes":           (70, 12),      "pass_pct":      (0.83, 0.05),
        "progressive_passes":(22, 8),      "shots":         (2.5, 1.2),
        "xa":               (0.18, 0.22),  "goals":         (0.3, 0.5),
        "assists":          (0.5, 0.6),    "dribbles_att":  (5,   2),
        "dribbles_won":     (3,   2),      "key_passes":    (3.0, 1.5),
        "pressures":        (15,  6),      "pressure_won":  (5,   3),
        "tackles_att":      (1,   1),      "tackles_won":   (1,   1),
        "interceptions":    (1,   1),      "aerial_att":    (2,   2),
        "aerial_won":       (1,   1),      "touches_box":   (5,   3),
        "saves":            (0,   0),      "match_rating":  (7.1, 0.7),
    },
    "LW": {
        "distance_m":       (11_000, 700), "hsr_m":         (1_300, 300),
        "sprint_m":         (550, 150),    "sprint_count":  (35, 10),
        "accel_count":      (35,  9),      "decel_count":   (32,  8),
        "max_speed_kmh":    (33.0, 2.0),   "player_load":   (415, 55),
        "passes":           (45, 10),      "pass_pct":      (0.80, 0.05),
        "progressive_passes":(16, 6),      "shots":         (2.5, 1.3),
        "xa":               (0.15, 0.20),  "goals":         (0.35, 0.6),
        "assists":          (0.30, 0.5),   "dribbles_att":  (6,   2),
        "dribbles_won":     (4,   2),      "key_passes":    (2.5, 1.2),
        "pressures":        (12,  5),      "pressure_won":  (4,   3),
        "tackles_att":      (1,   1),      "tackles_won":   (1,   1),
        "interceptions":    (1,   1),      "aerial_att":    (2,   2),
        "aerial_won":       (1,   1),      "touches_box":   (4,   3),
        "saves":            (0,   0),      "match_rating":  (7.0, 0.7),
    },
    "ST": {
        "distance_m":       (10_000, 600), "hsr_m":         (1_200, 280),
        "sprint_m":         (500, 140),    "sprint_count":  (30,  9),
        "accel_count":      (32,  8),      "decel_count":   (28,  7),
        "max_speed_kmh":    (32.5, 2.0),   "player_load":   (390, 50),
        "passes":           (35,  8),      "pass_pct":      (0.77, 0.06),
        "progressive_passes":(10, 4),      "shots":         (4.0, 1.5),
        "xa":               (0.10, 0.15),  "goals":         (0.5, 0.7),
        "assists":          (0.2, 0.4),    "dribbles_att":  (4,   2),
        "dribbles_won":     (2,   2),      "key_passes":    (1.5, 1.0),
        "pressures":        (10,  4),      "pressure_won":  (3,   3),
        "tackles_att":      (1,   1),      "tackles_won":   (0,   1),
        "interceptions":    (0,   1),      "aerial_att":    (5,   3),
        "aerial_won":       (3,   2),      "touches_box":   (6,   4),
        "saves":            (0,   0),      "match_rating":  (7.0, 0.7),
    },
}
# Mirror RB ↔ LB,  RW ↔ LW
POSITION_PROFILES["RB"] = POSITION_PROFILES["LB"]
POSITION_PROFILES["RW"] = POSITION_PROFILES["LW"]

# Session-type scaling (fraction of full-match profile)
SESSION_FACTORS: dict[str, dict[str, float]] = {
    "MD":   {"d": 1.00, "hi": 1.00, "pl": 1.00, "dur": 92,  "rpe": 7.5},
    "MD+1": {"d": 0.28, "hi": 0.18, "pl": 0.28, "dur": 33,  "rpe": 3.8},
    "MD-3": {"d": 0.85, "hi": 0.82, "pl": 0.83, "dur": 70,  "rpe": 7.0},
    "MD-2": {"d": 0.62, "hi": 0.60, "pl": 0.62, "dur": 58,  "rpe": 5.8},
    "MD-1": {"d": 0.28, "hi": 0.25, "pl": 0.28, "dur": 33,  "rpe": 4.5},
    "GYM":  {"d": 0.07, "hi": 0.04, "pl": 0.48, "dur": 68,  "rpe": 7.8},
}

ACWR_ZONE_ORDER  = ["Under-training", "Optimal", "Caution", "High Risk"]

def acwr_zone(value: float) -> str:
    for name, (lo, hi, _, _) in ACWR_ZONES.items():
        if lo <= value < hi:
            return name
    return "High Risk"
