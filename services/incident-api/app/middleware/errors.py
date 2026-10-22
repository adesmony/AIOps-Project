from uuid import uuid4

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.contracts import ErrorCode, ErrorEnvelope
from app.contracts.api import ErrorDetail
from app.errors import AppError

logger = structlog.get_logger("errors")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _response(
    request: Request,
    status_code: int,
    code: ErrorCode,
    message: str,
    details=None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorDetail(code=code, message=message, details=details),
        requestId=_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(by_alias=True, mode="json"),
    )


async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
    logger.warning(
        "request_failed",
        request_id=_request_id(request),
        error_code=error.code.value,
        status_code=error.status_code,
    )
    return _response(request, error.status_code, error.code, error.message, error.details)


async def validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
        for item in error.errors()
    ]
    return _response(
        request,
        422,
        ErrorCode.VALIDATION_ERROR,
        "Request validation failed",
        details,
    )


async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    logger.error(
        "unhandled_request_error",
        request_id=_request_id(request),
        error_type=type(error).__name__,
    )
    return _response(
        request,
        500,
        ErrorCode.INTERNAL_ERROR,
        "An internal error occurred",
    )
