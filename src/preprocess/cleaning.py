import pandas as pd

from src.data_ingestion.schema import normalize_topic


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned.drop_duplicates(subset=["content_id"], keep="first")
    cleaned = cleaned.dropna(subset=["timestamp"])
    cleaned["timestamp"] = pd.to_datetime(cleaned["timestamp"], errors="coerce")
    cleaned = cleaned.dropna(subset=["timestamp"])
    cleaned["text"] = cleaned["text"].fillna("").astype(str)
    cleaned["topic"] = cleaned["topic"].fillna("other").map(normalize_topic)
    cleaned["duration"] = pd.to_numeric(cleaned["duration"], errors="coerce").fillna(0)
    cleaned["like"] = pd.to_numeric(cleaned["like"], errors="coerce").fillna(0)
    cleaned["comment"] = pd.to_numeric(cleaned["comment"], errors="coerce").fillna(0)
    cleaned["share"] = pd.to_numeric(cleaned["share"], errors="coerce").fillna(0)
    return cleaned.reset_index(drop=True)
