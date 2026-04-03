from __future__ import annotations

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

    role = str(payload.get("role", "viewer"))

    return UserIdentity(username=sub, role=role)


