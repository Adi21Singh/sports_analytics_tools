"""Player role clustering via K-means + PCA dimensionality reduction."""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


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


def cluster_players(
    match_players: pd.DataFrame,
    n_clusters: int = 5,
    seed: int = 42,
) -> pd.DataFrame:
    """
    K-means cluster on match-averaged stats.

    Returns a player-level DataFrame with columns:
      player_id, player_name, position, <features>, cluster, cluster_label, pca_x, pca_y
    """
    agg = (
        match_players
        .groupby(["player_id", "player_name", "position"])[CLUSTER_FEATURES]
        .mean()
        .reset_index()
    )

    X = agg[CLUSTER_FEATURES].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    km = KMeans(n_clusters=n_clusters, random_state=seed, n_init="auto")
    agg["cluster"] = km.fit_predict(X_scaled)

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
