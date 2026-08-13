from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.diagnoses.models import Damage, Diagnosis


class DiagnosisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, diagnosis: Diagnosis) -> Diagnosis:
        self.session.add(diagnosis)
        await self.session.flush()
        await self.session.refresh(diagnosis)
        return diagnosis

    async def add_damages(self, damages: list[Damage]) -> None:
        self.session.add_all(damages)
        await self.session.flush()

    async def get_by_id(self, diagnosis_id: UUID) -> Diagnosis | None:
        return await self.session.get(Diagnosis, diagnosis_id)

    async def get_owned_by_id(self, *, diagnosis_id: UUID, user_id: UUID) -> Diagnosis | None:
        return await self.session.scalar(
            select(Diagnosis).where(
                Diagnosis.id == diagnosis_id,
                Diagnosis.user_id == user_id,
            )
        )

    async def list_damages(self, *, diagnosis_id: UUID) -> list[Damage]:
        result = await self.session.scalars(
            select(Damage)
            .where(Damage.diagnosis_id == diagnosis_id)
            .order_by(Damage.sort_order.asc(), Damage.created_at.asc())
        )
        return list(result.all())
