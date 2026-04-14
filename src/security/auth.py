from __future__ import annotations

import hashlib
import hmac
import re
import threading
from dataclasses import dataclass

from src.repositories.factory import get_user_repository
from src.repositories.interfaces import UserEntity
from src.config.settings import settings


@dataclass
class UserIdentity:
    username: str
    role: str


_USERS_LOCK = threading.Lock()
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def _hash_password(password: str) -> str:
    secret = settings.app_secret.encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()


def _to_identity(user: UserEntity) -> UserIdentity:
    role = _normalize_role(str(user.role or "user"))
    return UserIdentity(username=user.username, role=role)


def _normalize_role(raw_role: str) -> str:
    if raw_role in {"admin", "user"}:
        return raw_role
    if raw_role in {"viewer", "researcher"}:
        return "user"
    return "user"


def _seed_admin_if_missing() -> None:
    repo = get_user_repository()
    repo.ensure_admin_user(_hash_password("admin123"))


def verify_login(username: str, password: str) -> UserIdentity | None:
    username = username.strip()
    if not username:
        return None
    with _USERS_LOCK:
        _seed_admin_if_missing()
        row = get_user_repository().get_by_username(username)
    if not row:
        return None
    if row.password_hash != _hash_password(password):
        return None
    return _to_identity(row)


def register_user(username: str, password: str) -> UserIdentity:
    """自助注册仅创建普通用户。"""
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise ValueError("invalid_username")
    if len(password) < 6:
        raise ValueError("password_too_short")
    with _USERS_LOCK:
        _seed_admin_if_missing()
        repo = get_user_repository()
        if repo.get_by_username(username):
            raise ValueError("username_taken")
        user = repo.create_user(username=username, password_hash=_hash_password(password), role="user")
    return _to_identity(user)


def change_password(username: str, old_password: str, new_password: str) -> None:
    username = username.strip()
    if len(new_password) < 6:
        raise ValueError("password_too_short")
    with _USERS_LOCK:
        repo = get_user_repository()
        row = repo.get_by_username(username)
        if not row:
            raise ValueError("user_not_found")
        if row.password_hash != _hash_password(old_password):
            raise ValueError("wrong_old_password")
        ok = repo.update_password(username, _hash_password(new_password))
        if not ok:
            raise ValueError("user_not_found")


def get_user_profile(username: str) -> UserEntity | None:
    return get_user_repository().get_by_username(username.strip())


def update_user_profile(
    username: str,
    *,
    nickname: str | None,
    email: str | None,
    phone: str | None,
    avatar: str | None,
) -> UserEntity | None:
    return get_user_repository().update_profile(
        username.strip(),
        nickname=nickname,
        email=email,
        phone=phone,
        avatar=avatar,
    )


def list_users() -> list[UserEntity]:
    return get_user_repository().list_users()


def update_user_role(username: str, role: str) -> UserEntity | None:
    normalized = _normalize_role(role)
    return get_user_repository().update_role(username.strip(), normalized)


def check_permission(role: str, action: str) -> bool:
    policy = {
        "admin": {"*"},
        "user": {"view", "run", "export"},
        "researcher": {"view", "run", "export"},
        "viewer": {"view", "run"},
    }
    allowed = policy.get(_normalize_role(role), {"view"})
    return "*" in allowed or action in allowed

