from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder

from src.data_ingestion.import_service import import_bytes

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/import")
async def import_rows(
    file: UploadFile = File(...),
    import_format: str = Query("auto", alias="format", description="auto | douyin | standard"),
) -> dict:
    name = file.filename or "upload.json"
    raw_fmt = (import_format or "auto").strip().lower()
    if raw_fmt not in {"auto", "douyin", "standard"}:
        raise HTTPException(status_code=400, detail="format 必须为 auto、douyin 或 standard")
    try:
        content = await file.read()
        df, used = import_bytes(content, name, raw_fmt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _log.exception("ingestion import failed: %s", name)
        raise HTTPException(status_code=400, detail=str(e)) from e
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {
        "rows": jsonable_encoder(records),
        "format": used,
        "row_count": len(records),
        "filename": name,
    }
