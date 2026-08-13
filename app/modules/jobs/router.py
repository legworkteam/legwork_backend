from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.api.dependencies.ownership import Principal, get_guest_or_member_principal
from app.core.responses import ApiResponse, success_response
from app.modules.jobs.schemas import JobSchema
from app.modules.jobs.service import JobService


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{jobId}",
    response_model=ApiResponse[JobSchema],
    summary="Get job status",
)
async def get_job(
    jobId: UUID,
    request: Request,
    principal: Principal = Depends(get_guest_or_member_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[JobSchema]:
    service = JobService(session)
    job = await service.get_owned_job(job_id=jobId, principal=principal)
    return success_response(data=job, request=request)
