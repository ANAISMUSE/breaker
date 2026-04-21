from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.llm import get_llm_provider


def run_multimodal_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    if df.empty:
        return {
            "trace": [
                trace_event(
                    agent="multimodalAgent",
                    status="degraded",
                    input_summary={"rows": 0},
                    output_summary={"rows": 0},
                    fallback="skip multimodal parsing on empty dataframe",
                )
            ],
            "confidence": {"multimodalAgent": 0.2},
        }

    try:
        provider = get_llm_provider()
        rows = []
        parse_failures = 0
        for row in df.to_dict(orient="records"):
            try:
                parsed = provider.parse_multimodal_context(
                    text=str(row.get("text", "")),
                    video_hint=str(row.get("video_url", "")) or None,
                    subtitles=[str(x) for x in row.get("subtitles", [])] if isinstance(row.get("subtitles"), list) else [],
                    bullet_comments=[str(x) for x in row.get("bullet_comments", [])]
                    if isinstance(row.get("bullet_comments"), list)
                    else [],
                )
                row["frame_summary"] = parsed.frame_summary
                row["audio_transcript"] = parsed.audio_transcript
                row["subtitle_summary"] = parsed.subtitle_summary
                row["bullet_comments_summary"] = parsed.bullet_comments_summary
                row["normalized_description"] = parsed.normalized_description
            except Exception:
                parse_failures += 1
                row["frame_summary"] = str(row.get("video_url", ""))
                row["audio_transcript"] = ""
                row["subtitle_summary"] = ""
                row["bullet_comments_summary"] = ""
                row["normalized_description"] = str(row.get("text", ""))[:800]
            rows.append(row)

        row_count = len(rows)
        status = "ok" if parse_failures == 0 else "degraded"
        fallback = None if parse_failures == 0 else "fallback to row-level textual summaries"
        confidence = clamp_confidence(0.9 - (parse_failures / max(1, row_count)))
        return {
            "df": pd.DataFrame(rows),
            "trace": [
                trace_event(
                    agent="multimodalAgent",
                    status=status,
                    input_summary={"rows": int(len(df))},
                    output_summary={"rows": row_count, "parse_failures": parse_failures},
                    fallback=fallback,
                )
            ],
            "confidence": {"multimodalAgent": confidence},
        }
    except Exception as exc:
        return {
            "trace": [
                trace_event(
                    agent="multimodalAgent",
                    status="degraded",
                    input_summary={"rows": int(len(df))},
                    output_summary={"rows": int(len(df)), "parse_failures": int(len(df))},
                    fallback="reuse pre-parse dataframe",
                )
            ],
            "errors": [error_event(agent="multimodalAgent", error=exc, fallback="reuse pre-parse dataframe")],
            "confidence": {"multimodalAgent": 0.1},
        }

