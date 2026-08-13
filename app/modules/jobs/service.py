from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.ownership import Principal, ensure_job_access
from app.core.config import settings
from app.core.enums import JobStatus, JobType, PrincipalType
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.jobs.models import Job
from app.modules.jobs.repository import JobRepository
from app.modules.jobs.schemas import JobSchema
from app.utils.datetime import now_kst


class JobService:
    def __init__(self, session: AsyncSession, repository: JobRepository | None = None) -> None:
        self.session = session
        self.repository = repository or JobRepository(session)

    async def create_job(
        self,
        *,
        principal: Principal,
        job_type: JobType,
        status: JobStatus = JobStatus.PENDING,
        progress: int = 0,
        result_json: dict | None = None,
        error_json: dict | None = None,
    ) -> JobSchema:
        self._validate_progress(progress)
        created_at = now_kst()
        job = Job(
            user_id=principal.owner_id if principal.type is PrincipalType.USER else None,
            guest_session_id=principal.owner_id if principal.type is PrincipalType.GUEST else None,
            type=job_type,
            status=status,
            progress=progress,
            result_json=result_json,
            error_json=error_json,
            created_at=created_at,
            updated_at=created_at,
            expires_at=created_at + timedelta(hours=settings.job_ttl_hours),
        )
        await self.repository.add(job)
        await self.session.commit()
        return JobSchema.model_validate(job)

    async def get_owned_job(self, *, job_id: UUID, principal: Principal) -> JobSchema:
        job = await self.repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        ensure_job_access(principal, user_id=job.user_id, guest_session_id=job.guest_session_id)
        return JobSchema.model_validate(job)

    async def update_status(
        self,
        *,
        job_id: UUID,
        status: JobStatus,
        progress: int | None = None,
        result_json: dict | None = None,
        error_json: dict | None = None,
    ) -> JobSchema:
        job = await self.repository.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found.")

        if progress is not None:
            self._validate_progress(progress)
            job.progress = progress
        job.status = status
        job.result_json = result_json
        job.error_json = error_json
        job.updated_at = now_kst()
        await self.session.commit()
        await self.session.refresh(job)
        return JobSchema.model_validate(job)

    @staticmethod
    def _validate_progress(progress: int) -> None:
        if progress < 0 or progress > 100:
            raise ValidationError("Job progress must be between 0 and 100.")
