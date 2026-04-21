from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.evaluation.index_pipeline import evaluate_cocoon_pdf36
from src.evaluation.metrics_v2 import collect_multimodal_evidence, embedding_vector_source


def run_eval_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    benchmark = state.get("benchmark", {})
    try:
        result = evaluate_cocoon_pdf36(df, benchmark, mode="static")
        evidence = collect_multimodal_evidence(df, top_k=3)
        vector_source = embedding_vector_source(df)
        blindspots: list[str] = []
        if not df.empty and "topic" in df.columns and isinstance(benchmark, dict):
            topic_weights = df["topic"].astype(str).value_counts(normalize=True).to_dict()
            for topic, weight in benchmark.items():
                if float(weight) > float(topic_weights.get(topic, 0.0)):
                    blindspots.append(str(topic))
        cocoon_index = float(getattr(result, "cocoon_index", 0.0) or 0.0)
        confidence = clamp_confidence(cocoon_index / 10.0)
        return {
            "evaluation_result": result,
            "evidence": evidence,
            "evaluation_meta": {
                "embedding_vector_source": vector_source,
                "evidence_count": len(evidence),
            },
            "blindspots": blindspots[:8],
            "trace": [
                trace_event(
                    agent="evalAgent",
                    status="ok",
                    input_summary={"rows": int(len(df)), "benchmark_topics": len(benchmark) if isinstance(benchmark, dict) else 0},
                    output_summary={
                        "cocoon_index": cocoon_index,
                        "embedding_vector_source": vector_source,
                        "evidence_count": len(evidence),
                    },
                )
            ],
            "confidence": {"evalAgent": confidence},
        }
    except Exception as exc:
        return {
            "evaluation_meta": {"embedding_vector_source": "none", "evidence_count": 0},
            "evidence": [],
            "blindspots": [],
            "trace": [
                trace_event(
                    agent="evalAgent",
                    status="degraded",
                    input_summary={"rows": int(len(df)), "benchmark_topics": len(benchmark) if isinstance(benchmark, dict) else 0},
                    output_summary={"cocoon_index": 0.0, "embedding_vector_source": "none", "evidence_count": 0},
                    fallback="return empty evaluation evidence and metadata",
                )
            ],
            "errors": [
                error_event(agent="evalAgent", error=exc, fallback="return empty evaluation evidence and metadata")
            ],
            "confidence": {"evalAgent": 0.0},
        }
