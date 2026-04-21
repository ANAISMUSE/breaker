from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict


def _merge_lists(left: list[Any] | None, right: list[Any] | None) -> list[Any]:
    return (left or []) + (right or [])


def _merge_dicts(left: Mapping[str, float] | None, right: Mapping[str, float] | None) -> dict[str, float]:
    out = dict(left or {})
    out.update(dict(right or {}))
    return out


class AgentState(TypedDict, total=False):
    rows: list[dict[str, Any]]
    benchmark: dict[str, float]
    sim_rounds: int
    df: Any
    evaluation_result: Any
    evaluation_meta: dict[str, Any]
    evidence: list[dict[str, Any]]
    blindspots: list[str]
    simulation_compare: dict[str, Any]
    policy_plan: list[dict[str, Any]]
    policy_context: dict[str, Any]
    ladder_plan: list[dict[str, Any]]
    session_feedback: list[str]
    history_feedback: list[str]
    semantic_enhanced: bool
    trace: Annotated[list[dict[str, Any]], _merge_lists]
    errors: Annotated[list[dict[str, Any]], _merge_lists]
    confidence: Annotated[dict[str, float], _merge_dicts]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def trace_event(
    *,
    agent: str,
    status: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    fallback: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "agent": agent,
        "status": status,
        "input": input_summary,
        "output": output_summary,
        "ts": _now_iso(),
    }
    if fallback:
        event["fallback"] = fallback
    return event


def error_event(*, agent: str, error: Exception, fallback: str) -> dict[str, Any]:
    return {
        "agent": agent,
        "error_type": error.__class__.__name__,
        "message": str(error),
        "fallback": fallback,
        "ts": _now_iso(),
    }
