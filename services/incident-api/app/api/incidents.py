from fastapi import APIRouter, Request

from app.contracts import AnalysisRequest, AnalysisResponse, DashboardMetrics
from app.dependencies import CurrentUser, ServicesDependency

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_metrics(
    _user: CurrentUser,
    services: ServicesDependency,
) -> DashboardMetrics:
    return await services.analyses.metrics()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_incident(
    body: AnalysisRequest,
    request: Request,
    _user: CurrentUser,
    services: ServicesDependency,
) -> AnalysisResponse:
    services.telemetry.event("incident_analysis_started", {"request_id": request.state.request_id})
    return await services.diagnosis.analyze(request.state.request_id, body)
