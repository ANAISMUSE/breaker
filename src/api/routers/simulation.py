from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter
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
        result = service.compare(profile, df, payload.benchmark, payload.rounds)
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

