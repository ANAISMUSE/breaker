from __future__ import annotations

import pandas as pd

from src.agents.policies import generate_ladder_plan


def run_plan_node(state: dict) -> dict:
    df: pd.DataFrame = state.get("df", pd.DataFrame())
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if (not df.empty and "topic" in df.columns) else []
    result = state["evaluation_result"]
    ladder_plan = generate_ladder_plan(result, top_topics)
    state["ladder_plan"] = ladder_plan
    state.setdefault("trace", []).append({"node": "plan", "steps": len(ladder_plan)})
    return state
