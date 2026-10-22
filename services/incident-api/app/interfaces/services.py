from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts import (
    AnalysisRequest,
    Citation,
    DashboardMetrics,
    DiagnosisOutput,
    PublicUser,
    RegisterRequest,
)


class DatabaseProvider(Protocol):
    def session(self) -> AbstractAsyncContextManager[AsyncSession]: ...

    async def health_check(self) -> bool: ...

    async def close(self) -> None: ...


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> Any | None: ...

    async def get_by_id(self, user_id: UUID) -> Any | None: ...

    async def create(self, request: RegisterRequest, password_hash: str) -> Any: ...


class EvidenceRepository(Protocol):
    async def search(
        self, request: AnalysisRequest, embedding: Sequence[float], limit: int
    ) -> Sequence[Citation]: ...


class AnalysisRepository(Protocol):
    async def record(self, request_id: str, is_incident: bool) -> None: ...

    async def metrics(self) -> DashboardMetrics: ...


class OpenAIProvider(Protocol):
    async def embed(self, text: str) -> Sequence[float]: ...

    async def diagnose(
        self, request: AnalysisRequest, labeled_context: str
    ) -> DiagnosisOutput: ...

    async def health_check(self) -> bool: ...


class AuthService(Protocol):
    async def register(self, request: RegisterRequest) -> PublicUser: ...

    async def login(self, email: str, password: str) -> tuple[PublicUser, str]: ...

    async def authenticate(self, token: str | None) -> PublicUser: ...


class Telemetry(Protocol):
    def event(self, name: str, properties: dict[str, str] | None = None) -> None: ...

    def exception(self, error: Exception, properties: dict[str, str] | None = None) -> None: ...
