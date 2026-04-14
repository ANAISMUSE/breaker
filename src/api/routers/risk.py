from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
import pandas as pd

from src.services.risk_service import RiskService
from src.twin.twin_builder import ensure_profile_dataframe

router = APIRouter(prefix="/risk", tags=["risk"])
service = RiskService()


class EvalIn(BaseModel):
    rows: list[dict]
    benchmark: dict[str, float]


@router.post("/overview")
def risk_overview(payload: EvalIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    return service.evaluate_overview_payload(df, payload.benchmark)


@router.post("/detail")
def risk_detail(payload: EvalIn) -> dict:
    df = ensure_profile_dataframe(pd.DataFrame(payload.rows))
    return service.evaluate_detail(df, payload.benchmark)

