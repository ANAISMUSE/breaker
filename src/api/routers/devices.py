from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.device_service import DeviceService

router = APIRouter(prefix="/devices", tags=["devices"])
service = DeviceService()


class DeviceIn(BaseModel):
    name: str
    platform: str


class StatusIn(BaseModel):
    status: str


class BatchDeleteIn(BaseModel):
    device_ids: list[str]


@router.get("")
def list_devices() -> list[dict]:
    return [d.__dict__ for d in service.list_devices()]


@router.post("")
def create_device(payload: DeviceIn) -> dict:
    return service.create_device(payload.name, payload.platform).__dict__


@router.patch("/{device_id}/status")
def update_status(device_id: str, payload: StatusIn) -> dict:
    row = service.set_status(device_id, payload.status)
    if not row:
        raise HTTPException(status_code=404, detail="device not found")
    return row.__dict__


@router.delete("/{device_id}")
def delete_device(device_id: str) -> dict:
    ok = service.delete_device(device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="device not found")
    return {"ok": True}


@router.delete("")
def batch_delete_devices(payload: BatchDeleteIn) -> dict:
    result = service.delete_devices(payload.device_ids)
    return {"ok": True, **result}

