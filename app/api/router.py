from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.responses import ApiResponse, success_response
from app.modules.auth.router import router as auth_router
from app.modules.files.router import router as files_router
from app.modules.guests.router import router as guests_router
from app.modules.jobs.router import router as jobs_router
from app.modules.products.router import router as products_router
from app.modules.users.router import router as users_router
from app.utils.datetime import now_kst


api_router = APIRouter()
# Backend A (Core & Commerce)
api_router.include_router(auth_router)
api_router.include_router(guests_router)
api_router.include_router(users_router)
api_router.include_router(products_router)


class HealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    app_env: str = Field(alias="appEnv")
    checked_at: datetime = Field(alias="checkedAt")


@api_router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="Health check",
    tags=["health"],
)
async def health_check(request: Request) -> ApiResponse[HealthResponse]:
    return success_response(
        data=HealthResponse(status="ok", appEnv=settings.app_env, checkedAt=now_kst()),
        request=request,
    )


# Backend B (Experience & AI)
api_router.include_router(jobs_router)
api_router.include_router(files_router)
