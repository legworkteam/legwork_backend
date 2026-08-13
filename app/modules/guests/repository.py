"""Persistence for guest sessions and QR context lookups."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.guests.models import GuestSession
from app.modules.stores.models import Campaign, QrCodeMapping, Store


class GuestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_qr_mapping(self, code: str) -> QrCodeMapping | None:
        return await self.session.scalar(
            select(QrCodeMapping).where(QrCodeMapping.code == code)
        )

    async def get_store(self, store_id: uuid.UUID) -> Store | None:
        return await self.session.get(Store, store_id)

    async def get_campaign(self, campaign_id: uuid.UUID) -> Campaign | None:
        return await self.session.get(Campaign, campaign_id)

    async def create_session(
        self,
        *,
        qr_code_id: uuid.UUID | None,
        expires_at: datetime,
    ) -> GuestSession:
        session = GuestSession(qr_code_id=qr_code_id, expires_at=expires_at)
        self.session.add(session)
        await self.session.flush()
        return session
