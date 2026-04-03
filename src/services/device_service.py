from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from src.storage.mysql_store import MySqlStore

@dataclass
class Device:
    device_id: str
    name: str
    platform: str
    status: str
    last_seen: str


class DeviceService:
    def __init__(self) -> None:
        self.mysql = MySqlStore.from_settings() if MySqlStore.enabled() else None

    def _path(self) -> Path:
        p = Path("data/devices.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("[]", encoding="utf-8")
        return p

    def _load(self) -> list[Device]:
        rows = json.loads(self._path().read_text(encoding="utf-8"))
        return [Device(**r) for r in rows]

    def _save(self, rows: list[Device]) -> None:
        self._path().write_text(json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2), encoding="utf-8")

    def list_devices(self) -> list[Device]:
        if self.mysql:
            rows = self.mysql.list_devices()
            return [Device(**r) for r in rows]
        return self._load()

    def create_device(self, name: str, platform: str) -> Device:
        rows = self.list_devices()
        did = f"dev_{len(rows)+1:03d}"
        row = Device(
            device_id=did,
            name=name,
            platform=platform,
            status="idle",
            last_seen=datetime.utcnow().isoformat() + "Z",
        )
        if self.mysql:
            self.mysql.upsert_device(row.__dict__)
        else:
            rows.append(row)
            self._save(rows)
        return row

    def set_status(self, device_id: str, status: str) -> Device | None:
        rows = self.list_devices()
        found: Device | None = None
        for r in rows:
            if r.device_id == device_id:
                r.status = status
                r.last_seen = datetime.utcnow().isoformat() + "Z"
                found = r
                break
        if self.mysql:
            if found:
                self.mysql.upsert_device(found.__dict__)
        else:
            self._save(rows)
        return found

