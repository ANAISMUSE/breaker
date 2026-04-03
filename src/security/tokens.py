from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from src.config.settings import settings

ALGORITHM = "HS256"
DEFAULT_EXPIRE_HOURS = 24


def create_access_token(username: str, role: str, *, expires_hours: int = DEFAULT_EXPIRE_HOURS) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, settings.app_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.app_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
