"""Player role clustering via K-means + PCA dimensionality reduction.

K-means caveats
---------------
K-means assumes roughly spherical, equal-sized clusters (minimises
within-cluster sum of squared Euclidean distances).  Football player profiles
typically violate this assumption - a goalkeeper and a striker have very
different feature distributions with no meaningful centroid between them.

This module now provides:
  cluster_evaluation()  - silhouette scores + inertia for k=2–8
  cluster_stability()   - Jaccard stability across 10 random seeds
  cluster_players()     - original clustering with PCA projection

Users should examine the elbow plot and silhouette scores before trusting
any particular k.  If silhouette < 0.25, the cluster structure is weak.
If the elbow is not clear, hierarchical clustering or GMM may be preferable.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


CLUSTER_FEATURES = [
    "distance_m", "hsr_m", "sprint_count",
    "passes", "shots", "tackles_won",
    "dribbles_won", "key_passes", "pressures",
]

# Descriptive archetype labels (applied to clusters by centroid proximity)
ARCHETYPES = [
    "Defensive Anchor",
    "Box-to-Box Dynamo",
    "Creative Playmaker",
    "Athletic Runner",
    "Goal-Threat Forward",
]


def _aggregate_features(match_players: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, StandardScaler]:
    """Aggregate per-match stats to player averages and scale."""
    agg = (
        match_players
        .groupby(["player_id", "player_name", "position"])[CLUSTER_FEATURES + ["match_rating"]]
        .mean()
        .reset_index()
    )
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(agg[CLUSTER_FEATURES].fillna(0).values)
    return agg, X_scaled, scaler


def cluster_evaluation(
    match_players: pd.DataFrame,
    k_range: range = range(2, 9),
    seed: int = 42,
) -> pd.DataFrame:
    """
    Return a DataFrame with silhouette score and inertia for each k in k_range.

    Use this to:
      - Pick k from the elbow in the inertia curve
      - Validate that the chosen k has silhouette > 0.25
      - Compare against a random baseline (silhouette ≈ 0)

    Returns columns: k, silhouette, inertia, silhouette_interpretation
    """
    _, X_scaled, _ = _aggregate_features(match_players)

    rows = []
    for k in k_range:
        if k >= len(X_scaled):          # can't have more clusters than players
            break
        km = KMeans(n_clusters=k, random_state=seed, n_init="auto")
        labels  = km.fit_predict(X_scaled)
        sil     = float(silhouette_score(X_scaled, labels)) if k > 1 else float("nan")
        inertia = float(km.inertia_)

        if   sil >= 0.50: interp = "Strong"
        elif sil >= 0.25: interp = "Reasonable"
        elif sil >= 0.10: interp = "Weak"
        else:             interp = "No structure"

        rows.append({"k": k, "silhouette": round(sil, 3),
                     "inertia": round(inertia, 1),
                     "silhouette_interpretation": interp})

    return pd.DataFrame(rows)


def cluster_stability(
    match_players: pd.DataFrame,
    n_clusters: int = 5,
    n_seeds: int = 10,
) -> dict:
    """
    Measure how stable cluster assignments are across different random seeds
    using pairwise Jaccard similarity of co-membership matrices.

    Returns:
      mean_jaccard  - average pairwise Jaccard (1.0 = perfectly stable)
      std_jaccard   - standard deviation across seed pairs
      interpretation - string label

    Jaccard > 0.80: stable
    Jaccard 0.60–0.80: moderately stable
    Jaccard < 0.60: unstable - don't trust the cluster labels
    """
    _, X_scaled, _ = _aggregate_features(match_players)
    n = len(X_scaled)

    # Build co-membership matrix for each seed
    co_matrices = []
    for s in range(n_seeds):
        km  = KMeans(n_clusters=n_clusters, random_state=s, n_init="auto")
        lbl = km.fit_predict(X_scaled)
        co  = (lbl[:, None] == lbl[None, :]).astype(float)
        co_matrices.append(co)

    # Pairwise Jaccard between all seed pairs
    jaccards = []
    for i in range(n_seeds):
        for j in range(i + 1, n_seeds):
            a, b = co_matrices[i], co_matrices[j]
            # Exclude diagonal (same player vs itself)
            mask     = ~np.eye(n, dtype=bool)
            inter    = (a[mask] * b[mask]).sum()
            union    = ((a[mask] + b[mask]) > 0).sum()
            jaccards.append(inter / union if union > 0 else 0.0)

    mean_j = float(np.mean(jaccards))
    std_j  = float(np.std(jaccards))

    if   mean_j >= 0.80: interp = "Stable - cluster labels are reliable"
    elif mean_j >= 0.60: interp = "Moderately stable - interpret with care"
    else:                interp = "Unstable - k-means solution is seed-dependent"

    return {"mean_jaccard": round(mean_j, 3),
            "std_jaccard":  round(std_j, 3),
            "interpretation": interp,
            "n_seeds": n_seeds,
            "n_clusters": n_clusters}


def cluster_players(
    match_players: pd.DataFrame,
    n_clusters: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """
    K-means cluster on match-averaged stats.

    Returns a player-level DataFrame with columns:
      player_id, player_name, position, <features>, cluster, cluster_label,
      pca_x, pca_y, explained_var_pct, silhouette_score
    """
    agg, X_scaled, scaler = _aggregate_features(match_players)

    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init="auto")
    agg["cluster"] = km.fit_predict(X_scaled)

    # Silhouette for the chosen k
    sil = float(silhouette_score(X_scaled, agg["cluster"])) if n_clusters > 1 else float("nan")
    agg["silhouette_score"] = round(sil, 3)

    # PCA for 2-D visualisation
    pca = PCA(n_components=2, random_state=seed)
    coords = pca.fit_transform(X_scaled)
    agg["pca_x"]            = coords[:, 0].round(3)
    agg["pca_y"]            = coords[:, 1].round(3)
    agg["explained_var_pct"]= round(float(pca.explained_variance_ratio_.sum()) * 100, 1)

    # Label clusters by which archetype their centroid most resembles
    centres_orig = scaler.inverse_transform(km.cluster_centers_)
    centroids_df = pd.DataFrame(centres_orig, columns=CLUSTER_FEATURES)

    labels = _assign_archetype_labels(centroids_df, n_clusters)
    agg["cluster_label"] = agg["cluster"].map(labels)

    return agg


def _assign_archetype_labels(centroids: pd.DataFrame, n_clusters: int) -> dict[int, str]:
    """
    Heuristically assign human-readable labels to cluster centroids.
    Ranks clusters on domain signals; falls back to generic names.
    """
    labels: dict[int, str] = {}
    used: set[str] = set()
    archetype_priority = {
        "Defensive Anchor": ("tackles_won", True),
        "Box-to-Box Dynamo":("distance_m",  True),
        "Creative Playmaker":("key_passes", True),
        "Athletic Runner":  ("hsr_m",       True),
        "Goal-Threat Forward":("shots",     True),
    }
    remaining = list(range(n_clusters))

    for archetype, (col, ascending_rank_high) in archetype_priority.items():
        if not remaining:
            break
        if col not in centroids.columns:
            continue
        best = max(remaining, key=lambda i: centroids.loc[i, col])
        if archetype not in used:
            labels[best] = archetype
            used.add(archetype)
            remaining.remove(best)

    for i, idx in enumerate(remaining):
        labels[idx] = f"Role Group {i + 1}"

    return labels
