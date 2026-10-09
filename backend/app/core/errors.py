import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict[str, Any]] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class NotFoundError(AppError):
    def __init__(self, resource_type: str, resource_id: str | int):
        super().__init__(
            code="NOT_FOUND", message=f"{resource_type} '{resource_id}' not found", status_code=404
        )


class ConflictError(AppError):
    def __init__(self, message: str, allowed: list[str] | None = None):
        details = [{"field": "allowed_transitions", "value": allowed}] if allowed else None
        super().__init__(code="CONFLICT", message=message, status_code=409, details=details)


class ValidationFailed(AppError):
    def __init__(self, message: str, details: list[dict[str, Any]] | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class PermissionDenied(AppError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class RateLimited(AppError):
    def __init__(self, message: str = "Too many requests", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(code="RATE_LIMITED", message=message, status_code=429)


class UnauthenticatedError(AppError):
    def __init__(self, message: str = "Unauthenticated"):
        super().__init__(code="UNAUTHENTICATED", message=message, status_code=401)


class InvalidCredentialsError(AppError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(code="INVALID_CREDENTIALS", message=message, status_code=401)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    # request.state.request_id should be set by the middleware
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    payload: dict[str, Any] = {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": request_id,
        }
    }

    headers = {}
    if isinstance(exc, RateLimited):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    details = []
    for error in exc.errors():
        details.append(
            {"field": "->".join(str(loc) for loc in error["loc"]), "message": error["msg"]}
        )

    payload: dict[str, Any] = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": details,
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=422, content=payload)


async def fallback_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    payload: dict[str, Any] = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": [],
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=500, content=payload)
