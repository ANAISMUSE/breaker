from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder

from src.data_ingestion.import_service import import_bytes
from src.embedding.pipeline import build_semantic_vector_store
from src.llm import get_llm_provider
from src.privacy.anonymizer import anonymize_record

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/import")
async def import_rows(
    file: UploadFile = File(...),
    import_format: str = Query("auto", alias="format", description="auto | douyin | standard"),
    semantic_enhance: bool = Query(True, description="Run LLM semantic extraction and embeddings"),
    anonymize: bool = Query(False, description="Anonymize records before returning"),
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

    llm_health = get_llm_provider().health()
    semantic_applied = False
    if semantic_enhance:
        if not llm_health.ok:
            raise HTTPException(status_code=400, detail=f"LLM is not ready: {llm_health.detail}")
        try:
            _, df = build_semantic_vector_store(df)
            semantic_applied = True
        except Exception as e:
            _log.exception("semantic enhancement failed: %s", name)
            raise HTTPException(status_code=502, detail=f"semantic enhancement failed: {e}") from e

    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    if anonymize:
        records = [anonymize_record(row) for row in records]
    return {
        "rows": jsonable_encoder(records),
        "format": used,
        "row_count": len(records),
        "filename": name,
        "semantic_enhanced": semantic_applied,
        "llm_provider": llm_health.provider,
        "embedding_model": llm_health.embedding_model,
        "multimodal_model": llm_health.multimodal_model,
        "anonymized": anonymize,
    }
