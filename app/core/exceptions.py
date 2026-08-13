from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response


class ErrorCode:
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    GUEST_SESSION_EXPIRED = "GUEST_SESSION_EXPIRED"
    GUEST_LIMIT_EXCEEDED = "GUEST_LIMIT_EXCEEDED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    GENERATION_FAILED = "GENERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = ErrorCode.INTERNAL_ERROR
    message = "서버 내부 오류가 발생했습니다."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = ErrorCode.VALIDATION_ERROR
    message = "입력값을 확인해주세요."


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.UNAUTHORIZED
    message = "인증이 필요합니다."


class TokenExpiredError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.TOKEN_EXPIRED
    message = "토큰이 만료되었습니다."


class GuestSessionExpiredError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.GUEST_SESSION_EXPIRED
    message = "게스트 세션이 만료되었습니다."


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.FORBIDDEN
    message = "접근 권한이 없습니다."


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.NOT_FOUND
    message = "리소스를 찾을 수 없습니다."


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.CONFLICT
    message = "요청 상태가 충돌했습니다."


class ProviderError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.AI_UNAVAILABLE
    message = "외부 Provider를 사용할 수 없습니다."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request=request,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message="입력값을 확인해주세요.",
                details={"errors": exc.errors()},
                request=request,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == status.HTTP_404_NOT_FOUND else ErrorCode.INTERNAL_ERROR
        message = "리소스를 찾을 수 없습니다." if exc.status_code == status.HTTP_404_NOT_FOUND else HTTPStatus(exc.status_code).phrase
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=code,
                message=message,
                request=request,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message="서버 내부 오류가 발생했습니다.",
                request=request,
            ),
        )
