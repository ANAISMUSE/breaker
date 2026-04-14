from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from src.compliance.audit import list_audit_logs

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


class PolicyIn(BaseModel):
    auto_cleanup_enabled: bool = False
    retention_hours: int = 24


@router.get("/audit")
def list_audit(limit: int = 100) -> list[dict]:
    return list_audit_logs(limit=limit)


@router.post("/audit")
def write_audit(payload: AuditIn) -> dict:
    service.audit(payload.event, payload.detail)
    return {"ok": True}


@router.post("/wipe")
def wipe(payload: WipeIn) -> dict:
    removed = service.wipe(payload.vector_store, payload.uploads, payload.tasks)
    return {"removed": removed}


@router.get("/policy")
def get_policy() -> dict:
    return service.get_policy()


@router.post("/policy")
def set_policy(payload: PolicyIn) -> dict:
    return service.set_policy(payload.auto_cleanup_enabled, payload.retention_hours)


@router.post("/auto-cleanup")
def run_auto_cleanup() -> dict:
    return service.run_auto_cleanup()


@router.get("/evidence")
def export_evidence(limit: int = 200) -> dict:
    return {"path": service.export_evidence(limit=limit)}

