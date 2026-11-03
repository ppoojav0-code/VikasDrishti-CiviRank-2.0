"""Explainable 0-100 development priority scoring."""

def calculate_priority_index(df):
    df = df.copy()
    # Indicators are normalized to 0..1. Higher is better except Crime.
    weights = {
        "Sanitation": 0.20, "Water": 0.20, "Housing": 0.15,
        "Roads": 0.10, "Drainage": 0.15, "Healthcare": 0.10,
        "Crime": 0.05, "Electricity": 0.05, "Education": 0.05,
    }
    available = [c for c in weights if c in df.columns]
    total = sum(weights[c] for c in available)
    score = 0
    for col in available:
        severity = df[col] if col == "Crime" else (1 - df[col])
        score = score + severity.fillna(0.5) * (weights[col] / total)
    df["Priority_Score"] = (score * 100).clip(0, 100).round(2)
    df["Rank"] = df["Priority_Score"].rank(ascending=False, method="dense").astype(int)

    def classify(value):
        if value >= 80: return "Critical"
        if value >= 60: return "High"
        if value >= 40: return "Medium"
        return "Low"

    df["Risk_Level"] = df["Priority_Score"].apply(classify)
    return df.sort_values("Priority_Score", ascending=False)
