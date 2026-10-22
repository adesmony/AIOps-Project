from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.images import IncidentImage


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(ApiModel):
    code: ErrorCode
    message: str
    details: Any | None = None


class ErrorEnvelope(ApiModel):
    error: ErrorDetail
    request_id: str = Field(alias="requestId")


class AnalysisRequest(ApiModel):
    image: IncidentImage | None = Field(default=None, exclude=True, repr=False)
    description: Annotated[str, Field(min_length=10, max_length=4000)]
    service: Annotated[str | None, Field(default=None, min_length=1, max_length=120)]
    time_window: Annotated[
        str | None, Field(default=None, alias="timeWindow", min_length=1, max_length=80)
    ]
    user_type: Literal["operator", "developer", "manager"] = Field(
        default="operator", alias="userType"
    )
    response_style: Literal["concise", "detailed", "executive"] = Field(
        default="concise", alias="responseStyle"
    )


class Citation(ApiModel):
    id: str = Field(min_length=1, max_length=100)
    source_type: Literal["runbook", "log", "metric", "knowledge"] = Field(alias="sourceType")
    source: str = Field(min_length=1, max_length=300)
    excerpt: str = Field(min_length=1, max_length=2000)
    observed_at: str | None = Field(default=None, alias="observedAt")
    row_id: str | None = Field(default=None, alias="rowId")
    issue_id: str | None = Field(default=None, alias="issueId")
    relevance: float | None = Field(default=None, ge=0, le=1)


class DiagnosisOutput(ApiModel):
    diagnosis: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(ge=0, le=1)
    citation_ids: list[str] = Field(alias="citationIds", max_length=25)
    recommended_human_actions: list[str] = Field(alias="recommendedHumanActions", max_length=12)
    limitations: list[str] = Field(max_length=12)
    prevention: list[str] = Field(default_factory=list, max_length=12)


class AnalysisResponse(ApiModel):
    request_id: str = Field(alias="requestId")
    diagnosis: str
    confidence: float = Field(ge=0, le=1)
    citations: list[Citation]
    recommended_human_actions: list[str] = Field(alias="recommendedHumanActions")
    limitations: list[str]
    prevention: list[str] = Field(default_factory=list)


class RequestDataPoint(ApiModel):
    label: str
    count: int = Field(ge=0)


class DashboardMetrics(ApiModel):
    total_api_requests: int = Field(alias="totalApiRequests", ge=0)
    total_incidents: int = Field(alias="totalIncidents", ge=0)
    total_non_errors: int = Field(alias="totalNonErrors", ge=0)
    requests_over_time: list[RequestDataPoint] = Field(alias="requestsOverTime")


class ServiceHealth(ApiModel):
    status: Literal["healthy", "unhealthy", "disabled"]
    essential: bool


class HealthResponse(ApiModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    services: dict[str, ServiceHealth]
