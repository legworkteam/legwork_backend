from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger
from app.core.responses import error_response

_logger = get_logger("exceptions")


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
    INVALID_IMAGE = "INVALID_IMAGE"
    PERSON_NOT_DETECTED = "PERSON_NOT_DETECTED"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    GENERATION_FAILED = "GENERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = ErrorCode.INTERNAL_ERROR
    message = "서버 오류가 발생했습니다."

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
    message = "요청이 현재 상태와 충돌합니다."


class ProviderError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.AI_UNAVAILABLE
    message = "AI Provider를 사용할 수 없습니다."


class ProductCodeNotDetectedError(ValidationError):
    code = "PRODUCT_CODE_NOT_DETECTED"
    message = "품번을 인식하지 못했습니다."


class ProductCodeAmbiguousError(ValidationError):
    code = "PRODUCT_CODE_AMBIGUOUS"
    message = "품번 후보가 여러 개 일치합니다."


class FileTooLargeError(ValidationError):
    code = ErrorCode.FILE_TOO_LARGE
    message = "파일 용량이 너무 큽니다."


class UnsupportedFileTypeError(ValidationError):
    code = ErrorCode.UNSUPPORTED_FILE_TYPE
    message = "지원하지 않는 파일 형식입니다."


class GuestLimitExceededError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = ErrorCode.GUEST_LIMIT_EXCEEDED
    message = "게스트 체험 가능 횟수를 초과했습니다."


class InvalidImageError(ValidationError):
    code = ErrorCode.INVALID_IMAGE
    message = "유효하지 않은 이미지입니다."


class PersonNotDetectedError(ValidationError):
    code = ErrorCode.PERSON_NOT_DETECTED
    message = "사진에서 인물을 인식하지 못했습니다."


class GenerationFailedError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.GENERATION_FAILED
    message = "가상 피팅 생성에 실패했습니다."


class RepairNotNeededError(ValidationError):
    code = "REPAIR_NOT_NEEDED"
    message = "이 진단 결과는 수리가 필요하지 않습니다."


class ReservationSlotUnavailableError(ConflictError):
    code = "REPAIR_SLOT_UNAVAILABLE"
    message = "선택한 수리 예약 슬롯을 사용할 수 없습니다."


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
                details={"errors": jsonable_encoder(exc.errors())},
                request=request,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = ErrorCode.NOT_FOUND if exc.status_code == status.HTTP_404_NOT_FOUND else ErrorCode.INTERNAL_ERROR
        message = (
            "리소스를 찾을 수 없습니다."
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else HTTPStatus(exc.status_code).phrase
        )
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
        request_id = getattr(request.state, "request_id", "req_unknown")
        _logger.exception(
            "Unhandled exception on %s %s (requestId=%s)",
            request.method,
            request.url.path,
            request_id,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message="서버 오류가 발생했습니다.",
                request=request,
            ),
        )
