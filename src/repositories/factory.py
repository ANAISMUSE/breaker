from __future__ import annotations

from src.config.settings import settings
from src.repositories.interfaces import TaskRepository, UserRepository
from src.repositories.task_repo_json import JsonTaskRepository
from src.repositories.task_repo_mysql import MySqlTaskRepository
from src.repositories.user_repo_mysql import MySqlUserRepository
from src.storage.mysql_store import MySqlStore


def get_task_repository() -> TaskRepository:
    if settings.storage_backend.lower() == "mysql" and MySqlStore.enabled():
        return MySqlTaskRepository()
    return JsonTaskRepository()


def get_user_repository() -> UserRepository:
    if settings.storage_backend.lower() == "mysql" and MySqlStore.enabled():
        return MySqlUserRepository()
    raise RuntimeError("MySQL user repository requires STORAGE_BACKEND=mysql and MYSQL_URL")

