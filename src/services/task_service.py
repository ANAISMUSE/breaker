from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import uuid

from src.repositories.factory import get_task_repository
from src.repositories.interfaces import TaskEntity
from src.web.task_store import append_task_log


@dataclass
class CreateTaskInput:
    name: str
    strategy: str
    rounds: int
    snapshot: dict


class TaskService:
    def __init__(self) -> None:
        self.repo = get_task_repository()

    def list_tasks(self) -> list[TaskEntity]:
        return self.repo.list_tasks()

    def create_task(self, inp: CreateTaskInput) -> TaskEntity:
        task = TaskEntity(
            task_id=str(uuid.uuid4()),
            name=inp.name,
            strategy=inp.strategy,
            status="pending",
            created_at=datetime.utcnow().isoformat() + "Z",
            rounds=inp.rounds,
            snapshot=inp.snapshot,
            task_logs=[],
        )
        return self.repo.create_task(task)

    def get_task(self, task_id: str) -> TaskEntity | None:
        return self.repo.get_task(task_id)

    def update_status(self, task_id: str, status: str) -> TaskEntity | None:
        updated = self.repo.update_task(task_id, {"status": status})
        if updated:
            append_task_log(task_id, "info", "task_status_updated", {"status": status})
            return self.repo.get_task(task_id)
        return None

    def append_snapshot(self, task_id: str, snapshot: dict) -> TaskEntity | None:
        cur = self.repo.get_task(task_id)
        if not cur:
            return None
        snaps = list(cur.snapshot.get("snapshots", []))
        snaps.append(
            {
                "ts": datetime.utcnow().isoformat() + "Z",
                "data": snapshot,
            }
        )
        merged = dict(cur.snapshot)
        merged["snapshots"] = snaps
        updated = self.repo.update_task(task_id, {"snapshot": merged})
        if updated:
            append_task_log(task_id, "info", "task_snapshot_appended", {"snapshot_keys": sorted(snapshot.keys())})
            return self.repo.get_task(task_id)
        return None

    def list_task_logs(self, task_id: str) -> list[dict]:
        row = self.repo.get_task(task_id)
        if not row:
            return []
        if not isinstance(row.task_logs, list):
            return []
        return row.task_logs

    def append_task_log(self, task_id: str, level: str, event: str, detail: dict) -> TaskEntity | None:
        row = append_task_log(task_id, level, event, detail)
        if not row:
            return None
        return self.repo.get_task(task_id)

    def export_task_logs_json(self, task_id: str) -> str | None:
        row = self.repo.get_task(task_id)
        if not row:
            return None
        out_dir = Path("outputs/task_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"task_logs_{task_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "task_id": row.task_id,
            "name": row.name,
            "strategy": row.strategy,
            "logs": row.task_logs if isinstance(row.task_logs, list) else [],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def export_task_json(self, task_id: str) -> str | None:
        row = self.repo.get_task(task_id)
        if not row:
            return None
        out_dir = Path("outputs/task_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"task_{task_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(row.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

