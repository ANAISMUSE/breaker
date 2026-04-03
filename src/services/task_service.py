from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import uuid

from src.repositories.factory import get_task_repository
from src.repositories.interfaces import TaskEntity


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
        )
        return self.repo.create_task(task)

    def get_task(self, task_id: str) -> TaskEntity | None:
        return self.repo.get_task(task_id)

    def update_status(self, task_id: str, status: str) -> TaskEntity | None:
        return self.repo.update_task(task_id, {"status": status})

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
        return self.repo.update_task(task_id, {"snapshot": merged})

    def export_task_json(self, task_id: str) -> str | None:
        row = self.repo.get_task(task_id)
        if not row:
            return None
        out_dir = Path("outputs/task_exports")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"task_{task_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(row.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

