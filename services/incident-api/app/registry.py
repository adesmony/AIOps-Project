from dataclasses import dataclass

from app.auth import JwtAuthService
from app.config import Settings, get_settings
from app.database import (
    SqlAnalysisRepository,
    SqlEvidenceRepository,
    SqlUserRepository,
    create_database_provider,
)
from app.diagnosis import DiagnosisService, create_openai_provider
from app.interfaces import (
    AnalysisRepository,
    AuthService,
    DatabaseProvider,
    EvidenceRepository,
    OpenAIProvider,
    Telemetry,
)
from app.telemetry import SafeTelemetry


@dataclass(frozen=True)
class Services:
    settings: Settings
    database: DatabaseProvider
    users: SqlUserRepository
    evidence: EvidenceRepository
    analyses: AnalysisRepository
    ai: OpenAIProvider
    auth: AuthService
    diagnosis: DiagnosisService
    telemetry: Telemetry


_services: Services | None = None


def initialize_services() -> Services:
    settings = get_settings()
    database = create_database_provider(settings)
    sessions = database.session_factory
    users = SqlUserRepository(sessions)
    evidence = SqlEvidenceRepository(sessions, settings)
    analyses = SqlAnalysisRepository(sessions)
    ai = create_openai_provider(settings)
    telemetry = SafeTelemetry(settings.applicationinsights_connection_string)
    return Services(
        settings=settings,
        database=database,
        users=users,
        evidence=evidence,
        analyses=analyses,
        ai=ai,
        auth=JwtAuthService(settings, users),
        diagnosis=DiagnosisService(settings, evidence, ai, analyses),
        telemetry=telemetry,
    )


def get_services() -> Services:
    global _services
    if _services is None:
        _services = initialize_services()
    return _services


def register_services(services: Services) -> None:
    global _services
    _services = services


def clear_services() -> None:
    global _services
    _services = None
