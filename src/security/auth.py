from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path

from src.config.settings import settings


@dataclass
class UserIdentity:
    username: str
    role: str


_USERS_LOCK = threading.Lock()
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def _users_file() -> Path:
    p = Path("data/users.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        seed = {
            "admin": {
                "password_hash": _hash_password("admin123"),
                "role": "admin",
            }
        }
        p.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _hash_password(password: str) -> str:
    secret = settings.app_secret.encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()


def _load_users() -> dict:
    raw = _users_file().read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


def _save_users(users: dict) -> None:
    text = json.dumps(users, ensure_ascii=False, indent=2) + "\n"
    _users_file().write_text(text, encoding="utf-8")


def verify_login(username: str, password: str) -> UserIdentity | None:
    with _USERS_LOCK:
        users = _load_users()
    row = users.get(username)
    if not row:
        return None
    if row.get("password_hash") != _hash_password(password):
        return None
    return UserIdentity(username=username, role=str(row.get("role", "viewer")))


def register_user(username: str, password: str) -> UserIdentity:
    """自助注册仅创建 viewer；admin/researcher 仍由 data/users.json 维护。"""
    if not _USERNAME_RE.match(username):
        raise ValueError("invalid_username")
    if len(password) < 6:
        raise ValueError("password_too_short")
    with _USERS_LOCK:
        users = _load_users()
        if username in users:
            raise ValueError("username_taken")
        users[username] = {"password_hash": _hash_password(password), "role": "viewer"}
        _save_users(users)
    return UserIdentity(username=username, role="viewer")


def change_password(username: str, old_password: str, new_password: str) -> None:
    if len(new_password) < 6:
        raise ValueError("password_too_short")
    with _USERS_LOCK:
        users = _load_users()
        row = users.get(username)
        if not row:
            raise ValueError("user_not_found")
        if row.get("password_hash") != _hash_password(old_password):
            raise ValueError("wrong_old_password")
        row["password_hash"] = _hash_password(new_password)
        users[username] = row
        _save_users(users)


def check_permission(role: str, action: str) -> bool:
    policy = {
        "admin": {"*"},
        "researcher": {"view", "run", "export"},
        "viewer": {"view"},
    }
    allowed = policy.get(role, {"view"})
    return "*" in allowed or action in allowed

