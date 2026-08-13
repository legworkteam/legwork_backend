from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Job
from app.modules.try_on.models import TryOn
from app.modules.diagnoses.models import Diagnosis


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, job: Job) -> Job:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_expired(self, *, now: datetime) -> list[Job]:
        result = await self.session.scalars(
            select(Job)
            .outerjoin(TryOn, TryOn.job_id == Job.id)
            .outerjoin(Diagnosis, Diagnosis.job_id == Job.id)
            .where(
                Job.expires_at <= now,
                TryOn.id.is_(None),
                Diagnosis.id.is_(None),
            )
        )
        return list(result.all())

    async def delete(self, job: Job) -> None:
        await self.session.delete(job)
