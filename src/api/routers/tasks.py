from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
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


class RunTaskIn(BaseModel):
    rows: list[dict] | None = None
    benchmark: dict[str, float] | None = None
    rounds: int | None = None
    device_id: str | None = None


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
def get_task_logs(
    task_id: str,
    level: str | None = None,
    event: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    row = service.get_task(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    payload = service.list_task_logs(
        task_id,
        level=level,
        event=event,
        start_ts=start_ts,
        end_ts=end_ts,
        page=page,
        page_size=page_size,
    )
    return {"task_id": task_id, **payload}


@router.post("/{task_id}/logs")
def write_task_log(task_id: str, payload: LogIn) -> dict:
    row = service.append_task_log(task_id, payload.level, payload.event, payload.detail)
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    return row.__dict__


@router.post("/{task_id}/run")
def run_task(task_id: str, payload: RunTaskIn) -> dict:
    row, run_result, reason = service.run_task(
        task_id,
        rows=payload.rows,
        benchmark=payload.benchmark,
        rounds=payload.rounds,
        device_id=payload.device_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="task not found")
    if run_result is None:
        if reason == "no_available_device":
            raise HTTPException(status_code=409, detail="no available device (idle) for this task")
        if reason == "missing_rows_or_benchmark":
            raise HTTPException(
                status_code=400,
                detail="task run requires rows and benchmark (provide payload or snapshot.rows/snapshot.benchmark)",
            )
        raise HTTPException(status_code=500, detail=f"task run failed: {reason or 'unknown_error'}")
    return {"task": row.__dict__, "run_result": run_result}


@router.get("/{task_id}/logs/export")
def export_task_logs(task_id: str) -> dict:
    out = service.export_task_logs_json(task_id)
    if not out:
        raise HTTPException(status_code=404, detail="task not found")
    return {"path": out}


@router.get("/{task_id}/logs/export.csv")
def export_task_logs_csv(
    task_id: str,
    level: str | None = None,
    event: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
) -> Response:
    out = service.export_task_logs_csv(task_id, level=level, event=event, start_ts=start_ts, end_ts=end_ts)
    if not out:
        raise HTTPException(status_code=404, detail="task not found")
    filename, content = out
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

