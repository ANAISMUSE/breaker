from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.embedding.pipeline import build_semantic_vector_store


def run_embed_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    if df.empty:
        return {
            "semantic_enhanced": False,
            "trace": [
                trace_event(
                    agent="embedAgent",
                    status="degraded",
                    input_summary={"rows": 0},
                    output_summary={"semantic_enhanced": False},
                    fallback="skip embedding on empty dataframe",
                )
            ],
            "confidence": {"embedAgent": 0.2},
        }
    try:
        _, enriched = build_semantic_vector_store(df)
        row_count = int(len(enriched))
        confidence = clamp_confidence(0.65 + min(0.3, row_count / 1000))
        return {
            "df": enriched,
            "semantic_enhanced": True,
            "trace": [
                trace_event(
                    agent="embedAgent",
                    status="ok",
                    input_summary={"rows": int(len(df))},
                    output_summary={"rows": row_count, "semantic_enhanced": True},
                )
            ],
            "confidence": {"embedAgent": confidence},
        }
    except Exception as exc:
        return {
            "semantic_enhanced": False,
            "trace": [
                trace_event(
                    agent="embedAgent",
                    status="degraded",
                    input_summary={"rows": int(len(df))},
                    output_summary={"rows": int(len(df)), "semantic_enhanced": False},
                    fallback="reuse pre-embedding dataframe",
                )
            ],
            "errors": [error_event(agent="embedAgent", error=exc, fallback="reuse pre-embedding dataframe")],
            "confidence": {"embedAgent": 0.1},
        }
