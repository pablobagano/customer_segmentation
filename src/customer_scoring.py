"""RFM scoring: apply the trained per-component KMeans models to a DataFrame."""


from __future__ import annotations


import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

SEGMENT_THRESHOLDS = [
    (7, "Premium"),
    (5, "Loyal"),
    (3, "Moderate"),
    (1, "Occasional"),
    (0, "Inactive"),
]


def cluster_rank_map(cluster_centers: np.ndarray, *, ascending: bool) -> dict[int, int]:
    """Map each cluster id to a 0..k-1 rank based on its center value.

    ascending=True  -> lowest center gets rank 0 (Frequency, Monetary: higher
                        raw value should score higher).
    ascending=False -> highest center gets rank 0 (Recency: lower raw value,
                        i.e. more recent, should score higher).
    """
    centers = cluster_centers.ravel()
    order = np.argsort(centers if ascending else -centers)
    return {int(cluster_id): int(rank) for rank, cluster_id in enumerate(order)}


def _segment_for_score(score:int)->str:
    for threshold, label in SEGMENT_THRESHOLDS:
        if score >= threshold:
            return label
    return "Inactive"


def score_rfm(
    df: pd.DataFrame,
    kmeans_freq: KMeans,
    kmeans_monetary: KMeans,
    kmeans_recency: KMeans,
) -> pd.DataFrame:
    """Apply the trained RFM KMeans models to df and return scored columns.

    df must contain Total_Purchases, Total_Spent, and Recency columns.
    Adds Cluster_*, *_Score, RMF_Score, Segmentation, and APV columns --
    same shape notebooks/customer_kmeans.ipynb produces.
    """
    out = df.copy()
    out["Cluster_Frequency"] = kmeans_freq.predict(out[["Total_Purchases"]])
    out["Cluster_Monetary"] = kmeans_monetary.predict(out[["Total_Spent"]])
    out["Cluster_Recency"] = kmeans_recency.predict(out[["Recency"]])

    freq_rank = cluster_rank_map(kmeans_freq.cluster_centers_, ascending=True)
    monetary_rank = cluster_rank_map(kmeans_monetary.cluster_centers_, ascending=True)
    recency_rank = cluster_rank_map(kmeans_recency.cluster_centers_, ascending=False)

    rank_dict = {"Frequency_Score":["Cluster_Frequency", freq_rank], 
    "Monetary_Score": ["Cluster_Monetary", monetary_rank], 
    "Recency_Score": ["Cluster_Recency", recency_rank]}

    for score, (cluster, rank) in rank_dict.items():
        out[score] = out[cluster].map(rank)
    

    out["RMF_Score"] = out[[score for score in rank_dict.keys()]].sum(axis=1)
    out["Segmentation"] = out["RMF_Score"].apply(_segment_for_score)
    out["APV"] = np.where(
        out["Total_Purchases"] > 0,
        out["Total_Spent"] / out["Total_Purchases"],
        0
    )

    
    return out

    