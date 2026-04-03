from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from sqlalchemy import JSON, Column, DateTime, Integer, MetaData, String, Table, create_engine, select, text
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from sqlalchemy.engine import Engine
    from sqlalchemy.engine.url import make_url

    HAS_SQLALCHEMY = True
except Exception:  # pragma: no cover - optional dependency fallback
    HAS_SQLALCHEMY = False
    Engine = Any  # type: ignore

from src.config.settings import settings

_log = logging.getLogger(__name__)
_SAFE_DB_NAME = re.compile(r"^[a-zA-Z0-9_]+$")


if HAS_SQLALCHEMY:
    metadata = MetaData()

    devices_table = Table(
        "devices",
        metadata,
        Column("device_id", String(64), primary_key=True),
        Column("name", String(255), nullable=False),
        Column("platform", String(64), nullable=False),
        Column("status", String(32), nullable=False),
        Column("last_seen", DateTime(), nullable=False),
    )

    simulation_records_table = Table(
        "simulation_records",
        metadata,
        Column("record_id", String(64), primary_key=True),
        Column("user_id", String(128), nullable=False),
        Column("rounds", Integer(), nullable=False),
        Column("benchmark", JSON(), nullable=False),
        Column("result", JSON(), nullable=False),
        Column("created_at", DateTime(), nullable=False),
    )

    tasks_table = Table(
        "tasks",
        metadata,
        Column("task_id", String(64), primary_key=True),
        Column("name", String(255), nullable=False),
        Column("strategy", String(64), nullable=False),
        Column("status", String(32), nullable=False),
        Column("created_at", DateTime(), nullable=False),
        Column("rounds", Integer(), nullable=False),
        Column("snapshot", JSON(), nullable=False),
    )

    persona_profiles_table = Table(
        "persona_profiles",
        metadata,
        Column("profile_id", String(64), primary_key=True),
        Column("user_id", String(128), nullable=False),
        Column("profile", JSON(), nullable=False),
        Column("created_at", DateTime(), nullable=False),
    )

    def ensure_mysql_database_exists(mysql_url: str) -> None:
        """若连接串中的库尚未创建，则在 MySQL 上执行 CREATE DATABASE（避免 1049 Unknown database）。"""
        u = make_url(mysql_url)
        db_name = u.database
        if not db_name:
            return
        if not _SAFE_DB_NAME.fullmatch(db_name):
            _log.warning("Skip auto-create DB: unsupported database name in URL")
            return
        bootstrap = u.set(database="mysql")
        eng = create_engine(bootstrap, isolation_level="AUTOCOMMIT", pool_pre_ping=True, future=True)
        with eng.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        eng.dispose()
        _log.info("MySQL database ready: %s", db_name)


@dataclass
class MySqlStore:
    engine: Engine

    @staticmethod
    def enabled() -> bool:
        return HAS_SQLALCHEMY and settings.storage_backend.lower() == "mysql" and bool(settings.mysql_url.strip())

    @classmethod
    def from_settings(cls) -> "MySqlStore":
        engine = create_engine(settings.mysql_url, pool_pre_ping=True, future=True)
        return cls(engine=engine)

    def init_tables(self) -> None:
        if HAS_SQLALCHEMY:
            ensure_mysql_database_exists(settings.mysql_url)
        metadata.create_all(self.engine)

    def list_devices(self) -> list[dict[str, Any]]:
        stmt = select(devices_table).order_by(devices_table.c.last_seen.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "device_id": r["device_id"],
                    "name": r["name"],
                    "platform": r["platform"],
                    "status": r["status"],
                    "last_seen": r["last_seen"].isoformat() + "Z",
                }
            )
        return out

    def upsert_device(self, row: dict[str, Any]) -> None:
        now = datetime.utcnow()
        payload = {
            "device_id": row["device_id"],
            "name": row["name"],
            "platform": row["platform"],
            "status": row["status"],
            "last_seen": now,
        }
        stmt = mysql_insert(devices_table).values(**payload)
        stmt = stmt.on_duplicate_key_update(
            name=stmt.inserted.name,
            platform=stmt.inserted.platform,
            status=stmt.inserted.status,
            last_seen=stmt.inserted.last_seen,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def create_simulation_record(
        self,
        record_id: str,
        user_id: str,
        rounds: int,
        benchmark: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                simulation_records_table.insert().values(
                    record_id=record_id,
                    user_id=user_id,
                    rounds=rounds,
                    benchmark=benchmark,
                    result=result,
                    created_at=datetime.utcnow(),
                )
            )

    def list_simulation_records(self, limit: int = 50) -> list[dict[str, Any]]:
        stmt = select(simulation_records_table).order_by(simulation_records_table.c.created_at.desc()).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "record_id": r["record_id"],
                    "user_id": r["user_id"],
                    "rounds": r["rounds"],
                    "benchmark": r["benchmark"],
                    "result": r["result"],
                    "created_at": r["created_at"].isoformat() + "Z",
                }
            )
        return out

    def create_persona_profile(self, profile_id: str, user_id: str, profile: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                persona_profiles_table.insert().values(
                    profile_id=profile_id,
                    user_id=user_id,
                    profile=profile,
                    created_at=datetime.utcnow(),
                )
            )

    def list_persona_profiles(self, limit: int = 50) -> list[dict[str, Any]]:
        stmt = select(persona_profiles_table).order_by(persona_profiles_table.c.created_at.desc()).limit(limit)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "profile_id": r["profile_id"],
                    "user_id": r["user_id"],
                    "profile": r["profile"],
                    "created_at": r["created_at"].isoformat() + "Z",
                }
            )
        return out

    def list_tasks(self) -> list[dict[str, Any]]:
        stmt = select(tasks_table).order_by(tasks_table.c.created_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "task_id": r["task_id"],
                    "name": r["name"],
                    "strategy": r["strategy"],
                    "status": r["status"],
                    "created_at": r["created_at"].isoformat() + "Z",
                    "rounds": r["rounds"],
                    "snapshot": r["snapshot"] or {},
                }
            )
        return out

    def create_task(self, row: dict[str, Any]) -> None:
        created_at_raw = str(row.get("created_at") or "")
        if created_at_raw.endswith("Z"):
            created_at_raw = created_at_raw[:-1]
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.utcnow()
        with self.engine.begin() as conn:
            conn.execute(
                tasks_table.insert().values(
                    task_id=row["task_id"],
                    name=row["name"],
                    strategy=row["strategy"],
                    status=row["status"],
                    created_at=created_at,
                    rounds=int(row.get("rounds", 0)),
                    snapshot=row.get("snapshot", {}) or {},
                )
            )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        stmt = select(tasks_table).where(tasks_table.c.task_id == task_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        return {
            "task_id": row["task_id"],
            "name": row["name"],
            "strategy": row["strategy"],
            "status": row["status"],
            "created_at": row["created_at"].isoformat() + "Z",
            "rounds": row["rounds"],
            "snapshot": row["snapshot"] or {},
        }

    def update_task(self, task_id: str, updates: dict[str, Any]) -> None:
        allowed = {"name", "strategy", "status", "rounds", "snapshot"}
        payload = {k: v for k, v in updates.items() if k in allowed}
        if not payload:
            return
        with self.engine.begin() as conn:
            conn.execute(tasks_table.update().where(tasks_table.c.task_id == task_id).values(**payload))

