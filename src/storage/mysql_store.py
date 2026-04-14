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

    users_table = Table(
        "users",
        metadata,
        Column("id", Integer(), primary_key=True, autoincrement=True),
        Column("username", String(64), nullable=False, unique=True),
        Column("password_hash", String(128), nullable=False),
        Column("role", String(16), nullable=False),
        Column("nickname", String(64), nullable=True),
        Column("email", String(255), nullable=True),
        Column("phone", String(32), nullable=True),
        Column("avatar", String(512), nullable=True),
        Column("created_at", DateTime(), nullable=False),
        Column("updated_at", DateTime(), nullable=False),
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
        self._ensure_users_schema()

    def _ensure_users_schema(self) -> None:
        statements = [
            "ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL",
        ]
        for stmt in statements:
            try:
                with self.engine.begin() as conn:
                    conn.execute(text(stmt))
            except Exception:
                # 兼容老库：列已存在时忽略，避免启动失败。
                _log.debug("Skip users schema patch: %s", stmt, exc_info=True)

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

    def delete_device(self, device_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(devices_table.delete().where(devices_table.c.device_id == device_id))
        return bool(result.rowcount and result.rowcount > 0)

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

    def get_persona_profile(self, profile_id: str) -> dict[str, Any] | None:
        stmt = select(persona_profiles_table).where(persona_profiles_table.c.profile_id == profile_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        return {
            "profile_id": row["profile_id"],
            "user_id": row["user_id"],
            "profile": row["profile"] or {},
            "created_at": row["created_at"].isoformat() + "Z",
        }

    def update_persona_profile(self, profile_id: str, user_id: str | None = None, profile: dict | None = None) -> bool:
        payload: dict[str, Any] = {}
        if user_id is not None:
            payload["user_id"] = user_id
        if profile is not None:
            payload["profile"] = profile
        if not payload:
            return False
        with self.engine.begin() as conn:
            result = conn.execute(
                persona_profiles_table.update().where(persona_profiles_table.c.profile_id == profile_id).values(**payload)
            )
        return bool(result.rowcount and result.rowcount > 0)

    def delete_persona_profile(self, profile_id: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(persona_profiles_table.delete().where(persona_profiles_table.c.profile_id == profile_id))
        return bool(result.rowcount and result.rowcount > 0)

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

    def _format_user_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "nickname": row.get("nickname"),
            "email": row.get("email"),
            "phone": row.get("phone"),
            "avatar": row.get("avatar"),
            "created_at": row["created_at"].isoformat() + "Z",
            "updated_at": row["updated_at"].isoformat() + "Z",
        }

    def ensure_admin_user(self, password_hash: str) -> None:
        now = datetime.utcnow()
        stmt = mysql_insert(users_table).values(
            username="admin",
            password_hash=password_hash,
            role="admin",
            nickname="系统管理员",
            email=None,
            phone=None,
            avatar=None,
            created_at=now,
            updated_at=now,
        )
        stmt = stmt.on_duplicate_key_update(username=stmt.inserted.username)
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        stmt = select(users_table).where(users_table.c.username == username)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if not row:
            return None
        return self._format_user_row(row)

    def list_users(self) -> list[dict[str, Any]]:
        stmt = select(users_table).order_by(users_table.c.created_at.desc())
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._format_user_row(row) for row in rows]

    def create_user(self, row: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow()
        payload = {
            "username": row["username"],
            "password_hash": row["password_hash"],
            "role": row["role"],
            "nickname": row.get("nickname"),
            "email": row.get("email"),
            "phone": row.get("phone"),
            "avatar": row.get("avatar"),
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as conn:
            conn.execute(users_table.insert().values(**payload))
        created = self.get_user_by_username(str(row["username"]))
        if not created:
            raise RuntimeError("failed_to_create_user")
        return created

    def update_user_password(self, username: str, password_hash: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                users_table.update()
                .where(users_table.c.username == username)
                .values(password_hash=password_hash, updated_at=datetime.utcnow())
            )
        return bool(result.rowcount and result.rowcount > 0)

    def update_user_profile(
        self,
        username: str,
        *,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {
            "nickname": nickname,
            "email": email,
            "phone": phone,
            "avatar": avatar,
            "updated_at": datetime.utcnow(),
        }
        with self.engine.begin() as conn:
            result = conn.execute(users_table.update().where(users_table.c.username == username).values(**payload))
        if not (result.rowcount and result.rowcount > 0):
            return None
        return self.get_user_by_username(username)

    def update_user_role(self, username: str, role: str) -> dict[str, Any] | None:
        with self.engine.begin() as conn:
            result = conn.execute(
                users_table.update().where(users_table.c.username == username).values(role=role, updated_at=datetime.utcnow())
            )
        if not (result.rowcount and result.rowcount > 0):
            return None
        return self.get_user_by_username(username)

