from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.data_ingestion.schema import normalize_topic
from src.twin.twin_builder import ensure_profile_dataframe


def run_ingest_node(state: AgentState) -> dict:
    rows = state.get("rows", [])
    try:
        df = ensure_profile_dataframe(pd.DataFrame(rows))
        if not df.empty and "topic" in df.columns:
            df["topic"] = df["topic"].astype(str).map(normalize_topic)
        row_count = int(len(df))
        confidence = clamp_confidence(0.6 + min(0.4, row_count / 500))
        return {
            "df": df,
            "trace": [
                trace_event(
                    agent="collectAgent",
                    status="ok",
                    input_summary={"rows": len(rows)},
                    output_summary={"rows": row_count, "topic_normalized": "topic" in df.columns},
                )
            ],
            "confidence": {"collectAgent": confidence},
        }
    except Exception as exc:
        return {
            "df": ensure_profile_dataframe(pd.DataFrame([])),
            "trace": [
                trace_event(
                    agent="collectAgent",
                    status="degraded",
                    input_summary={"rows": len(rows)},
                    output_summary={"rows": 0},
                    fallback="return empty normalized dataframe",
                )
            ],
            "errors": [error_event(agent="collectAgent", error=exc, fallback="return empty normalized dataframe")],
            "confidence": {"collectAgent": 0.0},
        }
