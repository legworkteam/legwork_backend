from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.enums import JobStatus
from app.core.exceptions import AppException, ErrorCode
from app.modules.jobs.service import JobService


async def run_job_with_new_session(
    *,
    job_id: UUID,
    runner: Callable[[AsyncSession, JobService, UUID], Awaitable[dict | None]],
) -> None:
    async with AsyncSessionLocal() as session:
        service = JobService(session)
        try:
            await service.update_status(job_id=job_id, status=JobStatus.PROCESSING, progress=1)
            result = await runner(session, service, job_id)
            await service.update_status(
                job_id=job_id,
                status=JobStatus.SUCCEEDED,
                progress=100,
                result_json=result,
                error_json=None,
            )
        except AppException as exc:
            await service.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                progress=100,
                result_json=None,
                error_json={"code": exc.code, "message": exc.message, "details": exc.details},
            )
        except Exception as exc:
            await service.update_status(
                job_id=job_id,
                status=JobStatus.FAILED,
                progress=100,
                result_json=None,
                error_json={"code": ErrorCode.INTERNAL_ERROR, "message": str(exc)},
            )
