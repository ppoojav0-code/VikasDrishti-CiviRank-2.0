"""K-means clustering with a consistent deprivation direction and readable profiles."""
import numpy as np
from sklearn.cluster import KMeans

INDICATORS = ["Sanitation", "Water", "Education", "Healthcare", "Crime",
              "Electricity", "Housing", "Roads", "Drainage"]


def apply_clustering(df, n_clusters=3):
    data = df.copy()
    features = [c for c in INDICATORS if c in data.columns]
    if len(data) < 2 or not features:
        data["Cluster"] = 0
        data["Cluster_Label"] = "Insufficient data for grouping"
        return data
    matrix = data[features].astype(float).copy()
    # Service indicators: lower means worse. Crime is severity: higher means worse.
    if "Crime" in matrix.columns:
        matrix["Crime"] = 1 - matrix["Crime"]
    matrix = matrix.replace([np.inf, -np.inf], np.nan).fillna(matrix.median()).fillna(0.5)
    count = max(2, min(int(n_clusters), len(data)))
    model = KMeans(n_clusters=count, random_state=42, n_init=20)
    raw = model.fit_predict(matrix)
    centers = model.cluster_centers_
    # Sort clusters from most deprived to least deprived for stable, interpretable numbering.
    order = np.argsort(centers.mean(axis=1))
    remap = {old: new for new, old in enumerate(order)}
    data["Cluster"] = [remap[x] for x in raw]
    labels = {}
    for old, new in remap.items():
        severity = float(centers[old].mean())
        if severity < 0.35:
            label = "Critical service gaps"
        elif severity < 0.55:
            label = "High service gaps"
        elif severity < 0.72:
            label = "Moderate service gaps"
        else:
            label = "Relatively better-served"
        labels[new] = label
    data["Cluster_Label"] = data["Cluster"].map(labels)
    return data
