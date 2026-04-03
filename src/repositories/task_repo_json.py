from __future__ import annotations

from src.repositories.interfaces import TaskEntity, TaskRepository
from src.web.task_store import create_task, get_task, list_tasks, update_task


class JsonTaskRepository(TaskRepository):
    def list_tasks(self) -> list[TaskEntity]:
        rows = list_tasks()
        return [
            TaskEntity(
                task_id=r.task_id,
                name=r.name,
                strategy=r.strategy,
                status=r.status,
                created_at=r.created_at,
                rounds=r.rounds,
                snapshot=r.snapshot,
            )
            for r in rows
        ]

    def create_task(self, task: TaskEntity) -> TaskEntity:
        row = create_task(task.name, task.strategy, task.rounds, task.snapshot)
        return TaskEntity(
            task_id=row.task_id,
            name=row.name,
            strategy=row.strategy,
            status=row.status,
            created_at=row.created_at,
            rounds=row.rounds,
            snapshot=row.snapshot,
        )

    def get_task(self, task_id: str) -> TaskEntity | None:
        row = get_task(task_id)
        if not row:
            return None
        return TaskEntity(
            task_id=row.task_id,
            name=row.name,
            strategy=row.strategy,
            status=row.status,
            created_at=row.created_at,
            rounds=row.rounds,
            snapshot=row.snapshot,
        )

    def update_task(self, task_id: str, updates: dict) -> TaskEntity | None:
        update_task(task_id, **updates)
        return self.get_task(task_id)

