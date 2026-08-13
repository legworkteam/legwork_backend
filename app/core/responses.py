from typing import Any, Generic, TypeVar

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class PaginationMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    next_cursor: str | None = Field(default=None, alias="nextCursor")
    has_next: bool = Field(default=False, alias="hasNext")
    limit: int


class ResponseMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    request_id: str = Field(alias="requestId")
    pagination: PaginationMeta | None = None


class ApiError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ApiError | None
    meta: ResponseMeta


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "req_unknown")


def success_response(
    *,
    data: T | None,
    request: Request,
    pagination: PaginationMeta | None = None,
) -> ApiResponse[T]:
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        meta=ResponseMeta(requestId=get_request_id(request), pagination=pagination),
    )


def error_response(
    *,
    code: str,
    message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = ApiResponse[Any](
        success=False,
        data=None,
        error=ApiError(code=code, message=message, details=details),
        meta=ResponseMeta(requestId=get_request_id(request)),
    )
    return response.model_dump(by_alias=True)
