from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TaskEntity:
    task_id: str
    name: str
    strategy: str
    status: str
    created_at: str
    rounds: int
    snapshot: dict
    task_logs: list[dict]


class TaskRepository(Protocol):
    def list_tasks(self) -> list[TaskEntity]:
        ...

    def create_task(self, task: TaskEntity) -> TaskEntity:
        ...

    def get_task(self, task_id: str) -> TaskEntity | None:
        ...

    def update_task(self, task_id: str, updates: dict) -> TaskEntity | None:
        ...


@dataclass
class UserEntity:
    username: str
    password_hash: str
    role: str
    nickname: str | None
    email: str | None
    phone: str | None
    avatar: str | None
    created_at: str
    updated_at: str


class UserRepository(Protocol):
    def ensure_admin_user(self, password_hash: str) -> None:
        ...

    def get_by_username(self, username: str) -> UserEntity | None:
        ...

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar: str | None = None,
    ) -> UserEntity:
        ...

    def update_password(self, username: str, password_hash: str) -> bool:
        ...

    def update_profile(
        self,
        username: str,
        *,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar: str | None = None,
    ) -> UserEntity | None:
        ...

    def list_users(self) -> list[UserEntity]:
        ...

    def update_role(self, username: str, role: str) -> UserEntity | None:
        ...

