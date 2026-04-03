from __future__ import annotations

from src.config.settings import settings
from src.repositories.interfaces import TaskRepository
from src.repositories.task_repo_json import JsonTaskRepository
from src.repositories.task_repo_mysql import MySqlTaskRepository
from src.storage.mysql_store import MySqlStore


def get_task_repository() -> TaskRepository:
    if settings.storage_backend.lower() == "mysql" and MySqlStore.enabled():
        return MySqlTaskRepository()
    return JsonTaskRepository()

