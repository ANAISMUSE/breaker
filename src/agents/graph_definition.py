from __future__ import annotations

from typing import Any

from src.agents.policies import generate_ladder_plan


def run_breakout_agent(state: dict[str, Any]) -> dict[str, Any]:
    result = state["evaluation_result"]
    top_topics = state.get("top_topics", [])
    state["ladder_plan"] = generate_ladder_plan(result, top_topics)
    return state
