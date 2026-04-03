from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.services.task_service import CreateTaskInput, TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])
service = TaskService()


class CreateTaskIn(BaseModel):
    name: str
    strategy: str
    rounds: int = 14
    snapshot: dict = {}


class StatusIn(BaseModel):
    status: str


class SnapshotIn(BaseModel):
    data: dict = {}


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
        return {}
    return row.__dict__


@router.patch("/{task_id}/status")
def update_status(task_id: str, payload: StatusIn) -> dict:
    row = service.update_status(task_id, payload.status)
    if not row:
        return {}
    return row.__dict__


@router.post("/{task_id}/snapshots")
def append_snapshot(task_id: str, payload: SnapshotIn) -> dict:
    row = service.append_snapshot(task_id, payload.data)
    if not row:
        return {}
    return row.__dict__


@router.get("/{task_id}/export")
def export_task(task_id: str) -> dict:
    out = service.export_task_json(task_id)
    return {"path": out}

