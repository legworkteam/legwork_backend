"""Persistence for User accounts (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuthProvider
from app.modules.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_local_by_email(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User).where(
                User.email == email,
                User.auth_provider == AuthProvider.LOCAL,
                User.deleted_at.is_(None),
            )
        )

    async def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    async def add(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
