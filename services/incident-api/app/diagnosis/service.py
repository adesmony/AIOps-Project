from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

from app.config import Settings
from app.contracts import AnalysisRequest, AnalysisResponse, Citation
from app.errors import AppError
from app.interfaces import AnalysisRepository, EvidenceRepository, OpenAIProvider


class DiagnosisService:
    def __init__(
        self,
        settings: Settings,
        evidence: EvidenceRepository,
        ai: OpenAIProvider,
        analyses: AnalysisRepository,
    ) -> None:
        self._settings = settings
        self._evidence = evidence
        self._ai = ai
        self._analyses = analyses

    def _bounded_context(self, citations: list[Citation]) -> str:
        blocks: list[str] = []
        used = 0
        for citation in citations[: self._settings.max_evidence_items]:
            block = (
                f"CITATION_ID: {citation.id}\n"
                f"SOURCE_TYPE: {citation.source_type}\n"
                f"SOURCE: {citation.source}\n"
                f"CONTENT: {citation.excerpt}\n"
            )
            if used + len(block) > self._settings.max_evidence_chars:
                break
            blocks.append(block)
            used += len(block)
        return "\n".join(blocks)

    async def analyze(self, request_id: str, request: AnalysisRequest) -> AnalysisResponse:
        try:
            embedding = await self._ai.embed(request.description)
            citations = list(
                await self._evidence.search(
                    request, embedding, self._settings.max_evidence_items
                )
            )
            output = await self._ai.diagnose(request, self._bounded_context(citations))
        except (TimeoutError, APITimeoutError) as error:
            raise AppError.timeout(
                "Analysis timed out before a complete response was returned"
            ) from error
        except (APIConnectionError, RateLimitError, InternalServerError) as error:
            raise AppError.unavailable("Azure OpenAI is temporarily unavailable") from error
        valid_ids = {citation.id for citation in citations}
        if any(citation_id not in valid_ids for citation_id in output.citation_ids):
            raise AppError.unavailable("Diagnosis cited evidence that was not retrieved")
        selected = [citation for citation in citations if citation.id in output.citation_ids]
        response = AnalysisResponse(
            requestId=request_id,
            diagnosis=output.diagnosis,
            confidence=output.confidence,
            citations=selected,
            recommendedHumanActions=output.recommended_human_actions,
            limitations=output.limitations,
        )
        await self._analyses.record(
            request_id,
            is_incident=response.confidence > 0 or bool(response.citations),
        )
        return response
