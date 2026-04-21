from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.data_ingestion.schema import normalize_topic
from src.services.simulation_service import SimulationService
from src.twin.twin_builder import build_digital_twin_profile, ensure_profile_dataframe
from src.web.charts import cocoon_trend_option

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])
service = SimulationService()


class CompareIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]
    rounds: int = 10
    llm_enabled: bool = False


class LadderPlanIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]
    user_id: str = "unknown"


class LadderFeedbackIn(BaseModel):
    score: float = 0.0
    note: str = ""


@router.post("/compare")
def compare(payload: CompareIn) -> dict:
    logger.info(
        "compare: rows=%d rounds=%d",
        len(payload.rows),
        payload.rounds,
    )

    try:
        df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
        if not df.empty:
            df["topic"] = df["topic"].astype(str).map(normalize_topic)
        profile = build_digital_twin_profile(df)
        result = service.compare(
            profile,
            df,
            payload.benchmark,
            payload.rounds,
            llm_enabled=bool(payload.llm_enabled),
        )
        series = {k: v.get("series", []) for k, v in result.items() if not k.startswith("_")}
        out = {
            "result": result,
            "trend_option": cocoon_trend_option(series),
        }
        try:
            user_id = (
                str(df["user_id"].iloc[0])
                if (not df.empty and "user_id" in df.columns)
                else "unknown"
            )
            service.create_record(
                user_id=user_id,
                rounds=payload.rounds,
                benchmark=payload.benchmark,
                result=out,
                rows=payload.rows,
            )
        except Exception:
            logger.exception("persist simulation record failed (response still returned)")
        logger.info("POST /api/simulation/compare ok")
        return out
    except Exception:
        logger.exception("compare failed")
        raise


@router.get("/records")
def list_sim_records(limit: int = 50) -> list[dict]:
    return [x.__dict__ for x in service.list_records(limit=limit)]


@router.post("/ladder/plan")
def create_ladder_plan(payload: LadderPlanIn) -> dict:
    rec = service.create_ladder_execution(user_id=payload.user_id, rows=payload.rows, benchmark=payload.benchmark)
    return rec.__dict__


@router.get("/ladder/records")
def list_ladder_records(limit: int = 50) -> list[dict]:
    return [x.__dict__ for x in service.list_ladder_executions(limit=limit)]


@router.get("/ladder/{execution_id}")
def get_ladder_execution(execution_id: str) -> dict:
    rec = service.get_ladder_execution(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="ladder execution not found")
    return rec.__dict__


@router.post("/ladder/{execution_id}/execute-step")
def execute_ladder_step(execution_id: str) -> dict:
    rec = service.execute_ladder_step(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="ladder execution not found")
    return rec.__dict__


@router.post("/ladder/{execution_id}/feedback")
def append_ladder_feedback(execution_id: str, payload: LadderFeedbackIn) -> dict:
    rec = service.append_ladder_feedback(execution_id, payload.score, payload.note)
    if not rec:
        raise HTTPException(status_code=404, detail="ladder execution not found")
    return rec.__dict__


@router.post("/ladder/{execution_id}/next-step")
def move_ladder_next(execution_id: str) -> dict:
    rec = service.move_ladder_next(execution_id)
    if not rec:
        raise HTTPException(status_code=404, detail="ladder execution not found")
    return rec.__dict__

