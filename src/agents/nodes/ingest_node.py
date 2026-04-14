from __future__ import annotations

import pandas as pd

from src.data_ingestion.schema import normalize_topic
from src.twin.twin_builder import ensure_profile_dataframe


def run_ingest_node(state: dict) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(state.get("rows", [])))
    if not df.empty and "topic" in df.columns:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    state["df"] = df
    state.setdefault("trace", []).append({"node": "ingest", "rows": int(len(df))})
    return state
