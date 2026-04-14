from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import csv
import io
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

    def list_task_logs(
        self,
        task_id: str,
        level: str | None = None,
        event: str | None = None,
        start_ts: str | None = None,
        end_ts: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        row = self.repo.get_task(task_id)
        if not row:
            return {"logs": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
        if not isinstance(row.task_logs, list):
            return {"logs": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        logs = row.task_logs
        if level:
            logs = [x for x in logs if str(x.get("level", "")).lower() == level.lower()]
        if event:
            event_kw = event.strip().lower()
            logs = [x for x in logs if event_kw in str(x.get("event", "")).lower()]
        start_dt = self._parse_iso_datetime(start_ts)
        end_dt = self._parse_iso_datetime(end_ts)
        if start_dt or end_dt:
            filtered_logs: list[dict] = []
            for x in logs:
                log_dt = self._parse_iso_datetime(str(x.get("ts", "")))
                if not log_dt:
                    continue
                if start_dt and log_dt < start_dt:
                    continue
                if end_dt and log_dt > end_dt:
                    continue
                filtered_logs.append(x)
            logs = filtered_logs

        logs = list(reversed(logs))
        safe_page = max(1, page)
        safe_page_size = max(1, min(100, page_size))
        total = len(logs)
        total_pages = (total + safe_page_size - 1) // safe_page_size
        start = (safe_page - 1) * safe_page_size
        end = start + safe_page_size
        return {
            "logs": logs[start:end],
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
        }

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        raw = value.strip()
        if not raw:
            return None
        if raw.endswith("Z"):
            raw = raw[:-1]
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

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

    def export_task_logs_csv(
        self,
        task_id: str,
        level: str | None = None,
        event: str | None = None,
        start_ts: str | None = None,
        end_ts: str | None = None,
    ) -> tuple[str, str] | None:
        row = self.repo.get_task(task_id)
        if not row:
            return None
        payload = self.list_task_logs(
            task_id=task_id,
            level=level,
            event=event,
            start_ts=start_ts,
            end_ts=end_ts,
            page=1,
            page_size=10000,
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ts", "level", "event", "detail"])
        for log in payload.get("logs", []):
            writer.writerow(
                [
                    str(log.get("ts", "")),
                    str(log.get("level", "")),
                    str(log.get("event", "")),
                    json.dumps(log.get("detail", {}), ensure_ascii=False),
                ]
            )
        filename = f"task_logs_{task_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return filename, buf.getvalue()

