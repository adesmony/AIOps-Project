import asyncio

from fastapi import APIRouter, Response, status

from app.contracts import HealthResponse
from app.contracts.api import ServiceHealth
from app.dependencies import ServicesDependency

router = APIRouter(prefix="/api", tags=["health"])


async def _check(check, timeout_seconds: float) -> bool:
    try:
        async with asyncio.timeout(timeout_seconds):
            return await check()
    except Exception:
        return False


@router.get("/health", response_model=HealthResponse)
async def health(response: Response, services: ServicesDependency) -> HealthResponse:
    database_ok, ai_ok = await asyncio.gather(
        _check(services.database.health_check, services.settings.database_timeout_seconds),
        _check(services.ai.health_check, services.settings.ai_timeout_seconds),
    )
    app_insights_enabled = bool(services.settings.applicationinsights_connection_string)
    checks = {
        "database": ServiceHealth(
            status="healthy" if database_ok else "unhealthy", essential=True
        ),
        "azureOpenAI": ServiceHealth(
            status="healthy" if ai_ok else "unhealthy", essential=True
        ),
        "applicationInsights": ServiceHealth(
            status="healthy" if app_insights_enabled else "disabled", essential=False
        ),
    }
    essential_healthy = database_ok and ai_ok
    enhancements_healthy = app_insights_enabled
    overall = "healthy" if essential_healthy and enhancements_healthy else "degraded"
    if not essential_healthy:
        overall = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, services=checks)
