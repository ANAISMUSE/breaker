from __future__ import annotations

import pandas as pd

from src.agents.policies import generate_ladder_plan
from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event


def _build_interest_topology(df: pd.DataFrame, top_topics: list[str]) -> dict:
    if df.empty or "topic" not in df.columns:
        return {"topic_weights": {}, "bridges": []}
    topic_series = df["topic"].astype(str).str.lower()
    topic_weights = topic_series.value_counts(normalize=True).head(8).to_dict()
    transitions: dict[tuple[str, str], int] = {}
    seq = topic_series.tolist()
    for idx in range(len(seq) - 1):
        pair = (seq[idx], seq[idx + 1])
        if pair[0] == pair[1]:
            continue
        transitions[pair] = transitions.get(pair, 0) + 1
    bridges = [
        {"from": p[0], "to": p[1], "count": c}
        for p, c in sorted(transitions.items(), key=lambda item: item[1], reverse=True)[:6]
    ]
    return {
        "topic_weights": {k: round(float(v), 4) for k, v in topic_weights.items()},
        "top_topics": [str(x).lower() for x in top_topics[:6]],
        "bridges": bridges,
    }


def run_policy_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    blindspots = [str(x) for x in (state.get("blindspots", []) or [])]
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if (not df.empty and "topic" in df.columns) else []
    compare = state.get("simulation_compare", {})
    best = compare.get("_best", {}) if isinstance(compare, dict) else {}
    history_feedback = []
    if isinstance(best, dict):
        history_feedback.append(f"simulation_best={best.get('name', '')}")
        history_feedback.append(f"simulation_drop={best.get('drop', 0.0)}")
    for key in ("session_feedback", "history_feedback"):
        existing = state.get(key, [])
        if isinstance(existing, list):
            history_feedback.extend(str(x) for x in existing[:4] if str(x).strip())

    interest_topology = _build_interest_topology(df, top_topics)
    result = state.get("evaluation_result")
    try:
        normalized = generate_ladder_plan(
            result=result,
            top_topics=top_topics[:6],
            blindspots=blindspots,
            interest_topology=interest_topology,
            history_feedback=history_feedback,
        )
        confidence = clamp_confidence(sum(float(x.get("confidence", 0.6)) for x in normalized) / max(1, len(normalized)))
        return {
            "policy_plan": normalized,
            "policy_context": {
                "blindspots": blindspots[:8],
                "interest_topology": interest_topology,
                "history_feedback": history_feedback[:8],
            },
            "trace": [
                trace_event(
                    agent="policyAgent",
                    status="ok",
                    input_summary={"blindspots": len(blindspots), "top_topics": len(top_topics)},
                    output_summary={
                        "steps": len(normalized),
                        "uses_simulation": bool(best),
                        "topology_bridges": len(interest_topology.get("bridges", [])),
                    },
                )
            ],
            "confidence": {"policyAgent": confidence},
        }
    except Exception as exc:
        return {
            "policy_plan": [],
            "trace": [
                trace_event(
                    agent="policyAgent",
                    status="degraded",
                    input_summary={"blindspots": len(blindspots), "top_topics": len(top_topics)},
                    output_summary={"steps": 0, "uses_simulation": bool(best)},
                    fallback="return empty policy plan",
                )
            ],
            "errors": [error_event(agent="policyAgent", error=exc, fallback="return empty policy plan")],
            "confidence": {"policyAgent": 0.0},
        }

