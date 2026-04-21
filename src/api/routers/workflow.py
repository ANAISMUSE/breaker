from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.graph_definition import run_breakout_agent

router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkflowRunIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]


@router.post("/run")
def run_workflow(payload: WorkflowRunIn) -> dict:
    try:
        state = run_breakout_agent(
            {
                "rows": payload.rows,
                "benchmark": payload.benchmark,
                "trace": [],
                "semantic_enhanced": False,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"workflow failed: {e}") from e

    result = state.get("evaluation_result")
    trace = state.get("trace", [])
    node_summaries = [
        {
            "agent": item.get("agent"),
            "status": item.get("status"),
            "input": item.get("input", {}),
            "output": item.get("output", {}),
            "fallback": item.get("fallback"),
        }
        for item in trace
        if isinstance(item, dict)
    ]
    return {
        "evaluation": result.__dict__ if result is not None else None,
        "evaluation_meta": state.get("evaluation_meta", {}),
        "evidence": state.get("evidence", []),
        "ladder_plan": state.get("ladder_plan", []),
        "policy_plan": state.get("policy_plan", []),
        "policy_context": state.get("policy_context", {}),
        "simulation_compare": state.get("simulation_compare", {}),
        "blindspots": state.get("blindspots", []),
        "trace": trace,
        "agent_trace": trace,
        "node_summaries": node_summaries,
        "errors": state.get("errors", []),
        "confidence": state.get("confidence", {}),
        "degraded": any(item.get("status") != "ok" for item in node_summaries),
        "semantic_enhanced": bool(state.get("semantic_enhanced", False)),
        "row_count": len(state.get("rows", payload.rows)),
    }
