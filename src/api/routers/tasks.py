from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.task_service import CreateTaskInput, TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])
service = TaskService()


class CreateTaskIn(BaseModel):
    name: str
    strategy: str
    rounds: int = 14
    snapshot: dict = Field(default_factory=dict)


class StatusIn(BaseModel):
    status: str


class SnapshotIn(BaseModel):
    data: dict = Field(default_factory=dict)


class LogIn(BaseModel):
    level: str = "info"
    event: str
    detail: dict = Field(default_factory=dict)


@router.get("")
def list_tasks() -> list[dict]:
    return [t.__dict__ for t in service.list_tasks()]


@router.post("")
def create_task(payload: CreateTaskIn) -> dict:
    row = service.create_task(
        CreateTaskInput(
            name=payload.name,
            strategy=payload.strategy,
            rounds=payload.rounds,
            snapshot=payload.snapshot,
        )
    )
    return row.__dict__


@router.get("/{task_id}")
def get_task(task_id: str) -> dict:
    row = service.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row.__dict__


@router.patch("/{task_id}/status")
def update_status(task_id: str, payload: StatusIn) -> dict:
    row = service.update_status(task_id, payload.status)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row.__dict__


@router.post("/{task_id}/snapshots")
def append_snapshot(task_id: str, payload: SnapshotIn) -> dict:
    row = service.append_snapshot(task_id, payload.data)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row.__dict__


@router.get("/{task_id}/export")
def export_task(task_id: str) -> dict:
    out = service.export_task_json(task_id)
    if not out:
        raise HTTPException(status_code=404, detail="task not found")
    return {"path": out}


@router.get("/{task_id}/logs")
def get_task_logs(task_id: str) -> dict:
    row = service.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return {"task_id": task_id, "logs": service.list_task_logs(task_id)}


@router.post("/{task_id}/logs")
def write_task_log(task_id: str, payload: LogIn) -> dict:
    row = service.append_task_log(task_id, payload.level, payload.event, payload.detail)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row.__dict__


@router.get("/{task_id}/logs/export")
def export_task_logs(task_id: str) -> dict:
    out = service.export_task_logs_json(task_id)
    if not out:
        raise HTTPException(status_code=404, detail="task not found")
    return {"path": out}

