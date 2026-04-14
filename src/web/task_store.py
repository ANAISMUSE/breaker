from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from src.compliance.audit import append_audit_log


TaskStatus = Literal["pending", "running", "completed", "stopped"]


@dataclass
class SimulationTaskRecord:
    task_id: str
    name: str
    strategy: str
    status: TaskStatus
    created_at: str
    rounds: int
    snapshot: dict[str, Any] = field(default_factory=dict)
    task_logs: list[dict[str, Any]] = field(default_factory=list)
    cocoon_series: list[float] = field(default_factory=list)
    best_strategy_hint: str = ""


def _store_path() -> Path:
    p = Path("data/tasks_store.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_all() -> list[dict[str, Any]]:
    path = _store_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_all(rows: list[dict[str, Any]]) -> None:
    _store_path().write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def list_tasks() -> list[SimulationTaskRecord]:
    return [SimulationTaskRecord(**r) for r in _load_all()]


def create_task(name: str, strategy: str, rounds: int, snapshot: dict[str, Any]) -> SimulationTaskRecord:
    ts = datetime.utcnow().isoformat() + "Z"
    rec = SimulationTaskRecord(
        task_id=str(uuid.uuid4()),
        name=name,
        strategy=strategy,
        status="pending",
        created_at=ts,
        rounds=rounds,
        snapshot=snapshot,
        task_logs=[
            {
                "ts": ts,
                "level": "info",
                "event": "task_created",
                "detail": {"strategy": strategy, "rounds": rounds},
            }
        ],
        cocoon_series=[],
        best_strategy_hint="",
    )
    rows = _load_all()
    rows.append(asdict(rec))
    _save_all(rows)
    append_audit_log("task_created", {"task_id": rec.task_id, "strategy": strategy})
    return rec


def update_task(task_id: str, **kwargs: Any) -> None:
    rows = _load_all()
    for r in rows:
        if r.get("task_id") == task_id:
            r.update({k: v for k, v in kwargs.items() if v is not None})
            break
    _save_all(rows)


def append_task_log(task_id: str, level: str, event: str, detail: dict[str, Any] | None = None) -> SimulationTaskRecord | None:
    detail = detail or {}
    rows = _load_all()
    updated: dict[str, Any] | None = None
    for r in rows:
        if r.get("task_id") == task_id:
            logs = r.get("task_logs")
            if not isinstance(logs, list):
                logs = []
            logs.append(
                {
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "level": level,
                    "event": event,
                    "detail": detail,
                }
            )
            r["task_logs"] = logs
            updated = r
            break
    _save_all(rows)
    if not updated:
        return None
    return SimulationTaskRecord(**updated)


def get_task(task_id: str) -> SimulationTaskRecord | None:
    for r in _load_all():
        if r.get("task_id") == task_id:
            return SimulationTaskRecord(**r)
    return None
