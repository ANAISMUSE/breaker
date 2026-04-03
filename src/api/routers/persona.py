from __future__ import annotations

import logging
import uuid

import pandas as pd
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from src.data_ingestion.schema import normalize_topic

_log = logging.getLogger(__name__)
from src.storage.mysql_store import MySqlStore
from src.twin.twin_builder import build_digital_twin_profile

router = APIRouter(prefix="/persona", tags=["persona"])


class RowsIn(BaseModel):
    rows: list[dict]


@router.post("/build")
def build_persona(payload: RowsIn) -> dict:
    df = pd.DataFrame(payload.rows)
    if "topic" in df.columns:
        df["topic"] = df["topic"].astype(str).map(normalize_topic)
    profile = build_digital_twin_profile(df)
    out = profile.to_json_safe_dict()

    if MySqlStore.enabled():
        try:
            store = MySqlStore.from_settings()
            user_id = str(df["user_id"].iloc[0]) if (not df.empty and "user_id" in df.columns) else "unknown"
            store.create_persona_profile(
                profile_id=str(uuid.uuid4()), user_id=user_id, profile=jsonable_encoder(out)
            )
        except Exception:
            _log.exception("persist persona profile failed (response still returned)")
    return out


@router.get("/records")
def list_persona_records(limit: int = 50) -> list[dict]:
    if not MySqlStore.enabled():
        return []
    store = MySqlStore.from_settings()
    return store.list_persona_profiles(limit=limit)

