from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])
service = ComplianceService()


class WipeIn(BaseModel):
    vector_store: bool = True
    uploads: bool = True
    tasks: bool = True


class AuditIn(BaseModel):
    event: str
    detail: dict = {}


@router.get("/audit")
def list_audit(limit: int = 100) -> list[dict]:
    p = Path("data/audit_log.jsonl")
    if not p.exists():
        return []
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        txt = line.strip()
        if not txt:
            continue
        try:
            rows.append(json.loads(txt))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]


@router.post("/audit")
def write_audit(payload: AuditIn) -> dict:
    service.audit(payload.event, payload.detail)
    return {"ok": True}


@router.post("/wipe")
def wipe(payload: WipeIn) -> dict:
    removed = service.wipe(payload.vector_store, payload.uploads, payload.tasks)
    return {"removed": removed}

