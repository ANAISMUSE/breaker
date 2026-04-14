from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer



from src.security.auth import UserIdentity

from src.security.tokens import decode_access_token



_bearer = HTTPBearer(auto_error=False)





def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> UserIdentity:

    if creds is None or not creds.credentials:

        raise HTTPException(status_code=401, detail="not authenticated")

    payload = decode_access_token(creds.credentials)

    if not payload:

        raise HTTPException(status_code=401, detail="invalid or expired token")

    sub = payload.get("sub")

    if not sub or not isinstance(sub, str):

        raise HTTPException(status_code=401, detail="invalid token payload")

    role = str(payload.get("role", "user"))

    return UserIdentity(username=sub, role=role)


def require_roles(roles: list[str]) -> Callable[[UserIdentity], UserIdentity]:
    allowed = {role.lower() for role in roles}

    def _require(user: UserIdentity = Depends(get_current_user)) -> UserIdentity:
        if user.role.lower() not in allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _require


