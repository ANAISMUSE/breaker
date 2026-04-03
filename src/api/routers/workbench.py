from __future__ import annotations

from typing import Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from src.agents.policies import generate_ladder_plan
from src.data_ingestion.schema import normalize_topic
from src.evaluation.index_pipeline import evaluate_cocoon_pdf36
from src.twin.twin_builder import ensure_profile_dataframe
from src.web.report_export import export_word_report

router = APIRouter(prefix="/workbench", tags=["workbench"])


class PlanIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]


class ReportIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]
    strategy_summary: Optional[str] = None
    platform_placeholder: Optional[str] = None


@router.post("/plan")
def plan(payload: PlanIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    if not df.empty:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    ev = evaluate_cocoon_pdf36(df, payload.benchmark, mode="static")
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if not df.empty else []
    ladder_plan = generate_ladder_plan(ev, top_topics)
    return {
        "evaluation": ev.__dict__,
        "ladder_plan": ladder_plan,
    }


@router.post("/report")
def report(payload: ReportIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    if not df.empty:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    ev = evaluate_cocoon_pdf36(df, payload.benchmark, mode="static")
    top_topics = df["topic"].astype(str).value_counts().index.tolist() if not df.empty else []
    ladder_plan = generate_ladder_plan(ev, top_topics)
    out = export_word_report(
        result=ev,
        ladder_plan=ladder_plan,
        df=df,
        strategy_summary=payload.strategy_summary,
        platform_placeholder=payload.platform_placeholder,
    )
    return {"path": out, "evaluation": ev.__dict__, "ladder_plan": ladder_plan}

