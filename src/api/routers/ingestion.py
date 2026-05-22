from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder

from src.data_ingestion.import_service import import_bytes
from src.embedding.pipeline import build_semantic_vector_store
from src.llm import get_llm_provider
from src.privacy.anonymizer import anonymize_record

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

# 内存中的语义增强任务状态跟踪
_enhance_tasks: dict[str, dict] = {}


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _run_semantic_enhance(task_id: str, df: pd.DataFrame) -> None:
    """后台执行语义增强，更新任务状态。"""
    try:
        _enhance_tasks[task_id]["status"] = "running"
        _, enriched_df = build_semantic_vector_store(df)
        records = enriched_df.where(pd.notnull(enriched_df), None).to_dict(orient="records")
        records = _json_safe(records)
        _enhance_tasks[task_id].update({
            "status": "completed",
            "rows": jsonable_encoder(records),
            "row_count": len(records),
            "vector_schema_version": enriched_df.attrs.get("vector_schema_version"),
            "multimodal_schema_version": enriched_df.attrs.get("multimodal_schema_version"),
        })
    except Exception as exc:
        _log.exception("semantic enhancement background task %s failed", task_id)
        _enhance_tasks[task_id].update({
            "status": "failed",
            "error": str(exc),
        })


@router.post("/import")
async def import_rows(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    import_format: str = Query("auto", alias="format", description="auto | douyin | xiaohongshu | weibo | standard"),
    semantic_enhance: bool = Query(True, description="Run LLM semantic extraction and embeddings"),
    anonymize: bool = Query(False, description="Anonymize records before returning"),
) -> dict:
    name = file.filename or "upload.json"
    raw_fmt = (import_format or "auto").strip().lower()
    if raw_fmt not in {"auto", "douyin", "xiaohongshu", "weibo", "standard"}:
        raise HTTPException(status_code=400, detail="format 必须为 auto、douyin、xiaohongshu、weibo 或 standard")
    try:
        content = await file.read()
        result = import_bytes(content, name, raw_fmt)
        df = result.dataframe
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _log.exception("ingestion import failed: %s", name)
        raise HTTPException(status_code=400, detail=str(e)) from e

    llm_health = get_llm_provider().health()
    semantic_applied = False
    enhance_task_id: Optional[str] = None

    if semantic_enhance:
        if not llm_health.ok:
            raise HTTPException(status_code=400, detail=f"LLM is not ready: {llm_health.detail}")
        # 语义增强改为后台异步执行，接口立即返回
        enhance_task_id = str(uuid.uuid4())
        _enhance_tasks[enhance_task_id] = {
            "status": "pending",
            "row_count": len(df),
            "filename": name,
        }
        background_tasks.add_task(_run_semantic_enhance, enhance_task_id, df.copy())
        semantic_applied = False  # 尚未完成，标记为 False

    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    records = _json_safe(records)
    if anonymize:
        records = [anonymize_record(row) for row in records]
    resp = {
        "rows": jsonable_encoder(records),
        "format": result.detected_format,
        "detected_platform": result.detected_platform,
        "row_count": len(records),
        "filename": name,
        "invalid_row_count": result.invalid_row_count,
        "invalid_rows": result.invalid_rows,
        "warnings": result.warnings,
        "semantic_enhanced": semantic_applied,
        "semantic_enhance_task_id": enhance_task_id,
        "vector_schema_version": df.attrs.get("vector_schema_version"),
        "multimodal_schema_version": df.attrs.get("multimodal_schema_version"),
        "llm_provider": llm_health.provider,
        "embedding_model": llm_health.embedding_model,
        "multimodal_model": llm_health.multimodal_model,
        "anonymized": anonymize,
    }
    return resp


@router.get("/enhance-status/{task_id}")
def get_enhance_status(task_id: str) -> dict:
    """查询语义增强后台任务的状态。"""
    if task_id not in _enhance_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _enhance_tasks[task_id]
