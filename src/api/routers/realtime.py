from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from src.compliance.audit import append_audit_log
from src.config.settings import settings
from src.data_ingestion.mediacrawler_adapter import crawl_public_data_with_meta

router = APIRouter(prefix="/realtime", tags=["realtime"])


def _output_file() -> Path:
    path = Path(settings.mediacrawler_output_file)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def _real_mode_gate_reason() -> str | None:
    if not settings.enable_cloud_monitor:
        return "ENABLE_CLOUD_MONITOR is false"
    if not settings.enable_real_crawler:
        return "ENABLE_REAL_CRAWLER is false"
    if not settings.crawler_legal_ack:
        return "CRAWLER_LEGAL_ACK is false"
    if not settings.mediacrawler_project_dir:
        return "MEDIACRAWLER_PROJECT_DIR is empty"
    return None


@router.get("/status")
def realtime_status() -> dict:
    adapter_ready = bool(settings.mediacrawler_project_dir)
    gate_reason = _real_mode_gate_reason()
    output_file = _output_file()

    return {
        "enabled": settings.enable_cloud_monitor,
        "adapter": "mediacrawler",
        "mode": "real" if gate_reason is None and adapter_ready else "demo",
        "real_mode_allowed": gate_reason is None,
        "gate_reason": gate_reason,
        "adapter_ready": adapter_ready,
        "project_dir": settings.mediacrawler_project_dir or None,
        "last_output_exists": output_file.exists(),
        "last_output_file": str(output_file),
        "legal_ack": settings.crawler_legal_ack,
        "allowed_purposes": [p.strip() for p in settings.crawler_allowed_purposes.split(",") if p.strip()],
    }


class CrawlPreviewIn(BaseModel):
    platform: str = "douyin"
    keyword: str = ""
    limit: int = Field(default=50, ge=1, le=200)
    purpose: str = "academic_research"


@router.post("/crawl-preview")
def crawl_preview(payload: CrawlPreviewIn) -> dict:
    gate_reason = _real_mode_gate_reason()
    append_audit_log(
        "realtime_crawl_requested",
        {
            "platform": payload.platform,
            "keyword": payload.keyword,
            "limit": payload.limit,
            "purpose": payload.purpose,
            "gate_reason": gate_reason,
        },
    )

    df, meta = crawl_public_data_with_meta(
        platform=payload.platform,
        keyword=payload.keyword,
        limit=payload.limit,
        purpose=payload.purpose,
    )
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    result_mode = str(meta.get("mode", "demo"))
    degraded = bool(meta.get("degraded", False))
    adapter_reason = str(meta.get("reason", "")).strip()
    reason = adapter_reason or gate_reason or ""
    legal_ack = bool(meta.get("legal_ack", settings.crawler_legal_ack))
    compliance_gate_reason = str(meta.get("compliance_gate_reason", gate_reason or "")).strip()
    purpose = str(meta.get("purpose", payload.purpose)).strip()
    purpose_allowed = bool(meta.get("purpose_allowed", False))

    append_audit_log(
        "realtime_crawl_finished",
        {
            "platform": payload.platform,
            "mode": result_mode,
            "degraded": degraded,
            "gate_reason": gate_reason,
            "reason": reason,
            "row_count": len(records),
            "legal_ack": legal_ack,
            "compliance_gate_reason": compliance_gate_reason,
            "purpose": purpose,
            "purpose_allowed": purpose_allowed,
        },
    )

    return {
        "rows": jsonable_encoder(records),
        "row_count": len(records),
        "mode": result_mode,
        "degraded": degraded,
        "reason": reason,
        "legal_ack": legal_ack,
        "compliance_gate_reason": compliance_gate_reason,
        "purpose": purpose,
        "purpose_allowed": purpose_allowed,
    }
