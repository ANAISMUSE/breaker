from __future__ import annotations

from src.repositories.interfaces import TaskEntity, TaskRepository
from src.storage.mysql_store import MySqlStore


class MySqlTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.store = MySqlStore.from_settings()

    def list_tasks(self) -> list[TaskEntity]:
        rows = self.store.list_tasks()
        return [TaskEntity(**r) for r in rows]

    def create_task(self, task: TaskEntity) -> TaskEntity:
        self.store.create_task(task.__dict__)
        return task

    def get_task(self, task_id: str) -> TaskEntity | None:
        row = self.store.get_task(task_id)
        if not row:
            return None
        return TaskEntity(**row)

    def update_task(self, task_id: str, updates: dict) -> TaskEntity | None:
        self.store.update_task(task_id, updates)
        return self.get_task(task_id)

