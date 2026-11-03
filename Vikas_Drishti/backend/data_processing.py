import pandas as pd


def load_data(file):
    return pd.read_csv(file) if file is not None else pd.read_csv("data/sample_slum_data.csv")


def clean_data(df):
    df = df.copy()
    numeric_cols = ["Population", "Sanitation", "Water", "Education", "Healthcare",
                    "Crime", "Electricity", "Housing", "Roads", "Drainage",
                    "Livelihood_Gap", "Unemployment_Rate"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            median = df[col].median()
            df[col] = df[col].fillna(50 if pd.isna(median) else median)
    if "Area" not in df.columns:
        df["Area"] = [f"Area {i + 1}" for i in range(len(df))]
    df["Area"] = df["Area"].fillna("Unknown Area")
    if "Population" not in df.columns:
        df["Population"] = 0
    return df


def normalize_data(df):
    """Convert documented 0–100 indicators to 0–1 without dataset-relative scaling."""
    df = df.copy()
    features = ["Sanitation", "Water", "Education", "Healthcare", "Crime",
                "Electricity", "Housing", "Roads", "Drainage"]
    for col in features:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            # Already-normalized datasets remain supported; standard CSVs use 0..100.
            if values.dropna().empty or values.dropna().max() > 1:
                values = values / 100.0
            df[col] = values.clip(0, 1).fillna(0.5)
    # These two optional indicators are gaps: larger values indicate greater need.
    for col in ["Livelihood_Gap", "Unemployment_Rate"]:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            if values.dropna().empty or values.dropna().max() > 1:
                values = values / 100.0
            df[col] = values.clip(0, 1).fillna(0.5)
    return df
