from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path


def _audit_path() -> Path:
    p = Path("data/audit_log.jsonl")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_audit_log(event: str, detail: dict | None = None) -> None:
    line = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "detail": detail or {},
    }
    with _audit_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def list_audit_logs(limit: int = 100) -> list[dict]:
    p = _audit_path()
    rows: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        txt = line.strip()
        if not txt:
            continue
        try:
            rows.append(json.loads(txt))
        except json.JSONDecodeError:
            continue
    return rows[-max(1, int(limit)) :][::-1]


def wipe_local_session_data(
    also_vector_store: bool = True,
    also_uploads: bool = True,
    also_tasks: bool = True,
) -> list[str]:
    """删除本地会话数据（不上传原则下的用户一键清理）。"""
    removed: list[str] = []
    paths = [
        Path("data/upload_tmp"),
        Path("data/mediacrawler_tmp.json"),
    ]
    if also_uploads:
        for p in paths:
            if p.exists():
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
                removed.append(str(p))
    if also_vector_store:
        vs = Path("data/vector_store.json")
        if vs.exists():
            vs.unlink()
            removed.append(str(vs))
    if also_tasks:
        tp = Path("data/tasks_store.json")
        if tp.exists():
            tp.unlink()
            removed.append(str(tp))
    append_audit_log("wipe_local_session_data", {"removed": removed})
    return removed
