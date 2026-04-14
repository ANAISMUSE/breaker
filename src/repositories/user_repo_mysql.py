from __future__ import annotations

from src.repositories.interfaces import UserEntity, UserRepository
from src.storage.mysql_store import MySqlStore


class MySqlUserRepository(UserRepository):
    def __init__(self) -> None:
        self.store = MySqlStore.from_settings()

    def ensure_admin_user(self, password_hash: str) -> None:
        self.store.ensure_admin_user(password_hash)

    def get_by_username(self, username: str) -> UserEntity | None:
        row = self.store.get_user_by_username(username)
        if not row:
            return None
        return UserEntity(**row)

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar: str | None = None,
    ) -> UserEntity:
        row = self.store.create_user(
            {
                "username": username,
                "password_hash": password_hash,
                "role": role,
                "nickname": nickname,
                "email": email,
                "phone": phone,
                "avatar": avatar,
            }
        )
        return UserEntity(**row)

    def update_password(self, username: str, password_hash: str) -> bool:
        return self.store.update_user_password(username, password_hash)

    def update_profile(
        self,
        username: str,
        *,
        nickname: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        avatar: str | None = None,
    ) -> UserEntity | None:
        row = self.store.update_user_profile(
            username,
            nickname=nickname,
            email=email,
            phone=phone,
            avatar=avatar,
        )
        if not row:
            return None
        return UserEntity(**row)

    def list_users(self) -> list[UserEntity]:
        rows = self.store.list_users()
        return [UserEntity(**row) for row in rows]

    def update_role(self, username: str, role: str) -> UserEntity | None:
        row = self.store.update_user_role(username, role)
        if not row:
            return None
        return UserEntity(**row)
