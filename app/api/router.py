from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.responses import ApiResponse, success_response
from app.utils.datetime import now_kst


api_router = APIRouter()


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
