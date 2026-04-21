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

    def get_device(self, device_id: str) -> Device | None:
        rows = self.list_devices()
        for row in rows:
            if row.device_id == device_id:
                return row
        return None

    def claim_device(self, device_id: str) -> Device | None:
        row = self.get_device(device_id)
        if not row:
            return None
        if row.status != "idle":
            return None
        return self.set_status(device_id, "running")

    def acquire_device(self, preferred_platform: str | None = None) -> Device | None:
        rows = self.list_devices()
        idle_rows = [r for r in rows if r.status == "idle"]
        if not idle_rows:
            return None
        preferred = (preferred_platform or "").strip().lower()
        target: Device | None = None
        if preferred:
            for row in idle_rows:
                if row.platform.strip().lower() == preferred:
                    target = row
                    break
        if target is None:
            target = idle_rows[0]
        return self.set_status(target.device_id, "running")

    def release_device(self, device_id: str, final_status: str = "idle") -> Device | None:
        return self.set_status(device_id, final_status)

    def delete_device(self, device_id: str) -> bool:
        if self.mysql:
            return self.mysql.delete_device(device_id)

        rows = self.list_devices()
        kept = [r for r in rows if r.device_id != device_id]
        if len(kept) == len(rows):
            return False
        self._save(kept)
        return True

    def delete_devices(self, device_ids: list[str]) -> dict[str, list[str]]:
        uniq_ids = [x for x in dict.fromkeys(device_ids) if x]
        deleted: list[str] = []
        missing: list[str] = []
        for device_id in uniq_ids:
            if self.delete_device(device_id):
                deleted.append(device_id)
            else:
                missing.append(device_id)
        return {"deleted": deleted, "missing": missing}

