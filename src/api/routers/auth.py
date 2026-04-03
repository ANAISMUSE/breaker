from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.deps import get_current_user
from src.security.auth import UserIdentity, change_password, register_user, verify_login
from src.security.tokens import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


@router.post("/login")
def login(payload: LoginIn) -> dict:
    ident = verify_login(payload.username, payload.password)
    if not ident:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_access_token(ident.username, ident.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": ident.username,
        "role": ident.role,
    }


@router.post("/register")
def register(payload: RegisterIn) -> dict:
    try:
        ident = register_user(payload.username.strip(), payload.password)
    except ValueError as e:
        code = str(e)
        if code == "invalid_username":
            raise HTTPException(
                status_code=400,
                detail="用户名须为 3–32 位字母、数字或下划线",
            )
        if code == "password_too_short":
            raise HTTPException(status_code=400, detail="密码至少 6 位")
        if code == "username_taken":
            raise HTTPException(status_code=409, detail="用户名已被占用")
        raise HTTPException(status_code=400, detail="注册失败")
    token = create_access_token(ident.username, ident.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": ident.username,
        "role": ident.role,
    }


@router.post("/change-password")
def change_password_api(
    payload: ChangePasswordIn,
    user: UserIdentity = Depends(get_current_user),
) -> dict:
    try:
        change_password(user.username, payload.old_password, payload.new_password)
    except ValueError as e:
        code = str(e)
        if code == "wrong_old_password":
            raise HTTPException(status_code=400, detail="当前密码不正确")
        if code == "password_too_short":
            raise HTTPException(status_code=400, detail="新密码至少 6 位")
        raise HTTPException(status_code=400, detail="修改失败")
    return {"ok": True}

