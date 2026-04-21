from __future__ import annotations

import pandas as pd

from src.agents.state_protocol import AgentState, clamp_confidence, error_event, trace_event
from src.agents.policies import generate_ladder_plan


def run_plan_node(state: AgentState) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if (not df.empty and "topic" in df.columns) else []
    result = state.get("evaluation_result")
    policy_plan = state.get("policy_plan", [])
    try:
        if isinstance(policy_plan, list) and policy_plan:
            ladder_plan = [
                {
                    "level": str(x.get("level", "L1")),
                    "topic": str(x.get("topic", "other")),
                    "reason": str(x.get("reason", "")),
                    "confidence": float(x.get("confidence", 0.6)),
                }
                for x in policy_plan
                if isinstance(x, dict)
            ]
        elif result is not None:
            ladder_plan = generate_ladder_plan(result, top_topics)
        else:
            ladder_plan = []
        confidence = clamp_confidence(sum(float(x.get("confidence", 0.6)) for x in ladder_plan) / max(1, len(ladder_plan)))
        return {
            "ladder_plan": ladder_plan,
            "trace": [
                trace_event(
                    agent="planAgent",
                    status="ok",
                    input_summary={"policy_steps": len(policy_plan) if isinstance(policy_plan, list) else 0},
                    output_summary={"steps": len(ladder_plan)},
                )
            ],
            "confidence": {"planAgent": confidence},
        }
    except Exception as exc:
        return {
            "ladder_plan": [],
            "trace": [
                trace_event(
                    agent="planAgent",
                    status="degraded",
                    input_summary={"policy_steps": len(policy_plan) if isinstance(policy_plan, list) else 0},
                    output_summary={"steps": 0},
                    fallback="return empty ladder plan",
                )
            ],
            "errors": [error_event(agent="planAgent", error=exc, fallback="return empty ladder plan")],
            "confidence": {"planAgent": 0.0},
        }
