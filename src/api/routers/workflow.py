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
    return {
        "evaluation": result.__dict__ if result is not None else None,
        "ladder_plan": state.get("ladder_plan", []),
        "trace": state.get("trace", []),
        "semantic_enhanced": bool(state.get("semantic_enhanced", False)),
        "row_count": len(state.get("rows", payload.rows)),
    }
