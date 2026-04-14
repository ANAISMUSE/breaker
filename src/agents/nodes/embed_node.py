from __future__ import annotations

import pandas as pd

from src.embedding.pipeline import build_semantic_vector_store


def run_embed_node(state: dict) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    if df.empty:
        state.setdefault("trace", []).append({"node": "embed", "applied": False, "reason": "empty_df"})
        return state
    _, enriched = build_semantic_vector_store(df)
    state["df"] = enriched
    state["semantic_enhanced"] = True
    state.setdefault("trace", []).append({"node": "embed", "applied": True, "rows": int(len(enriched))})
    return state
