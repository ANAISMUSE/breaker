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

