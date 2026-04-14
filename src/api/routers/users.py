from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.api.deps import get_current_user, require_roles
from src.security.auth import (
    UserIdentity,
    get_user_profile,
    list_users,
    update_user_profile,
    update_user_role,
)

router = APIRouter(prefix="/users", tags=["users"])
PHONE_RE = re.compile(r"^\+?[0-9\- ]{6,20}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class UserProfileOut(BaseModel):
    username: str
    role: str
    nickname: str | None = None
    email: str | None = None
    phone: str | None = None
    avatar: str | None = None
    created_at: str
    updated_at: str


class UserProfilePatchIn(BaseModel):
    nickname: str | None = Field(default=None, max_length=64)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    avatar: str | None = Field(default=None, max_length=512)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        normalized = value.strip()
        if not PHONE_RE.fullmatch(normalized):
            raise ValueError("invalid phone format")
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        normalized = value.strip()
        if not EMAIL_RE.fullmatch(normalized):
            raise ValueError("invalid email format")
        return normalized

    @field_validator("avatar")
    @classmethod
    def validate_avatar(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        normalized = value.strip()
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("avatar must be a valid http(s) url")
        return normalized


class UserRolePatchIn(BaseModel):
    role: Literal["admin", "user"]


def _to_profile_payload(row: object) -> UserProfileOut:
    return UserProfileOut.model_validate(row, from_attributes=True)


@router.get("/me")
def get_me(user: UserIdentity = Depends(get_current_user)) -> UserProfileOut:
    row = get_user_profile(user.username)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return _to_profile_payload(row)


@router.patch("/me")
def patch_me(payload: UserProfilePatchIn, user: UserIdentity = Depends(get_current_user)) -> UserProfileOut:
    row = update_user_profile(
        user.username,
        nickname=payload.nickname,
        email=payload.email,
        phone=payload.phone,
        avatar=payload.avatar,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return _to_profile_payload(row)


@router.get("", dependencies=[Depends(require_roles(["admin"]))])
def admin_list_users() -> list[UserProfileOut]:
    return [_to_profile_payload(row) for row in list_users()]


@router.patch("/{username}/role", dependencies=[Depends(require_roles(["admin"]))])
def admin_patch_role(username: str, payload: UserRolePatchIn) -> UserProfileOut:
    row = update_user_role(username, payload.role)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return _to_profile_payload(row)
