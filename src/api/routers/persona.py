from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.persona_service import PersonaService

router = APIRouter(prefix="/persona", tags=["persona"])
service = PersonaService()


class RowsIn(BaseModel):
    rows: list[dict]


class PersonaCreateIn(BaseModel):
    user_id: str = "unknown"
    profile: dict = Field(default_factory=dict)


class PersonaUpdateIn(BaseModel):
    user_id: str | None = None
    profile: dict | None = None


@router.post("/build")
def build_persona(payload: RowsIn) -> dict:
    record = service.create_profile_from_rows(payload.rows)
    return {
        "profile_id": record.profile_id,
        "user_id": record.user_id,
        "created_at": record.created_at,
        "profile": record.profile,
    }


@router.post("/profiles")
def create_profile(payload: PersonaCreateIn) -> dict:
    row = service.create_profile(payload.user_id, payload.profile)
    return row.__dict__


@router.get("/profiles")
def list_persona_profiles(limit: int = 50) -> list[dict]:
    return [x.__dict__ for x in service.list_profiles(limit=limit)]


@router.get("/profiles/{profile_id}")
def get_persona_profile(profile_id: str) -> dict:
    row = service.get_profile(profile_id)
    if not row:
        raise HTTPException(status_code=404, detail="persona profile not found")
    return row.__dict__


@router.patch("/profiles/{profile_id}")
def update_persona_profile(profile_id: str, payload: PersonaUpdateIn) -> dict:
    row = service.update_profile(profile_id, user_id=payload.user_id, profile=payload.profile)
    if not row:
        raise HTTPException(status_code=404, detail="persona profile not found")
    return row.__dict__


@router.delete("/profiles/{profile_id}")
def delete_persona_profile(profile_id: str) -> dict:
    ok = service.delete_profile(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="persona profile not found")
    return {"ok": True}


@router.get("/records")
def list_persona_records(limit: int = 50) -> list[dict]:
    # Backward-compatible alias.
    return [x.__dict__ for x in service.list_profiles(limit=limit)]

