from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
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
    INVALID_IMAGE = "INVALID_IMAGE"
    PERSON_NOT_DETECTED = "PERSON_NOT_DETECTED"
    AI_TIMEOUT = "AI_TIMEOUT"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    GENERATION_FAILED = "GENERATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = ErrorCode.INTERNAL_ERROR
    message = "Server error."

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
    message = "Validation failed."


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.UNAUTHORIZED
    message = "Authentication required."


class TokenExpiredError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.TOKEN_EXPIRED
    message = "Token expired."


class GuestSessionExpiredError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.GUEST_SESSION_EXPIRED
    message = "Guest session expired."


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.FORBIDDEN
    message = "Forbidden."


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.NOT_FOUND
    message = "Resource not found."


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.CONFLICT
    message = "Conflict."


class ProviderError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.AI_UNAVAILABLE
    message = "AI provider is unavailable."


class ProductCodeNotDetectedError(ValidationError):
    code = "PRODUCT_CODE_NOT_DETECTED"
    message = "Product code not detected."


class ProductCodeAmbiguousError(ValidationError):
    code = "PRODUCT_CODE_AMBIGUOUS"
    message = "Multiple product-code candidates matched."


class FileTooLargeError(ValidationError):
    code = ErrorCode.FILE_TOO_LARGE
    message = "File is too large."


class UnsupportedFileTypeError(ValidationError):
    code = ErrorCode.UNSUPPORTED_FILE_TYPE
    message = "Unsupported file type."


class GuestLimitExceededError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = ErrorCode.GUEST_LIMIT_EXCEEDED
    message = "Guest try-on limit exceeded."


class InvalidImageError(ValidationError):
    code = ErrorCode.INVALID_IMAGE
    message = "Invalid image."


class PersonNotDetectedError(ValidationError):
    code = ErrorCode.PERSON_NOT_DETECTED
    message = "Person not detected."


class GenerationFailedError(AppException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = ErrorCode.GENERATION_FAILED
    message = "Try-on generation failed."


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
                message="Validation failed.",
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
            "Resource not found."
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
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=ErrorCode.INTERNAL_ERROR,
                message="Server error.",
                request=request,
            ),
        )
