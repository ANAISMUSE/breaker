from __future__ import annotations

import json

from src.services.device_service import DeviceService


def test_acquire_and_release_device_with_platform_preference(tmp_path, monkeypatch) -> None:
    devices_path = tmp_path / "devices.json"
    devices_path.write_text(
        json.dumps(
            [
                {
                    "device_id": "dev_001",
                    "name": "d1",
                    "platform": "douyin",
                    "status": "idle",
                    "last_seen": "2026-04-16T00:00:00Z",
                },
                {
                    "device_id": "dev_002",
                    "name": "d2",
                    "platform": "weibo",
                    "status": "idle",
                    "last_seen": "2026-04-16T00:00:00Z",
                },
            ]
        ),
        encoding="utf-8",
    )
    service = DeviceService()
    monkeypatch.setattr(service, "_path", lambda: devices_path)
    service.mysql = None

    locked = service.acquire_device(preferred_platform="weibo")
    assert locked is not None
    assert locked.device_id == "dev_002"
    assert locked.status == "running"

    after_lock = service.get_device("dev_002")
    assert after_lock is not None
    assert after_lock.status == "running"

    released = service.release_device("dev_002", final_status="idle")
    assert released is not None
    assert released.status == "idle"
