from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from src.services.device_service import DeviceService
from src.services.task_service import TaskService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _recent_audits(limit: int = 20) -> list[dict]:
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


@router.get("/dashboard")
def dashboard_summary() -> dict:
    task_service = TaskService()
    device_service = DeviceService()
    tasks = task_service.list_tasks()
    devices = device_service.list_devices()

    task_status_counts: dict[str, int] = {}
    for t in tasks:
        task_status_counts[t.status] = task_status_counts.get(t.status, 0) + 1

    device_status_counts: dict[str, int] = {}
    platform_counts: dict[str, int] = {}
    for d in devices:
        device_status_counts[d.status] = device_status_counts.get(d.status, 0) + 1
        platform_counts[d.platform] = platform_counts.get(d.platform, 0) + 1

    return {
        "task_count": len(tasks),
        "device_count": len(devices),
        "task_status_counts": task_status_counts,
        "device_status_counts": device_status_counts,
        "platform_counts": platform_counts,
        "recent_tasks": [t.__dict__ for t in tasks[-10:][::-1]],
        "recent_audits": _recent_audits(20),
    }

