from typing import Any

from app.contracts import ErrorCode


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details

    @classmethod
    def bad_request(cls, message: str) -> "AppError":
        return cls(400, ErrorCode.BAD_REQUEST, message)

    @classmethod
    def conflict(cls, message: str) -> "AppError":
        return cls(409, ErrorCode.CONFLICT, message)

    @classmethod
    def unauthorized(cls, message: str = "Authentication required") -> "AppError":
        return cls(401, ErrorCode.UNAUTHORIZED, message)

    @classmethod
    def unavailable(cls, message: str) -> "AppError":
        return cls(503, ErrorCode.SERVICE_UNAVAILABLE, message)

    @classmethod
    def timeout(cls, message: str) -> "AppError":
        return cls(504, ErrorCode.TIMEOUT, message)
