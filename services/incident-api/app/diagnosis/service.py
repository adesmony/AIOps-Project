import json

from openai import APIError, APITimeoutError

from app.config import Settings
from app.contracts import AnalysisRequest, AnalysisResponse, Citation, DiagnosisOutput
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
                f"UNTRUSTED_RECORD: {json.dumps(citation.model_dump(by_alias=True))}\n"
            )
            if used + len(block) + 1 > self._settings.max_evidence_chars:
                break
            blocks.append(block)
            used += len(block) + 1
        return "\n".join(blocks)

    async def analyze(self, request_id: str, request: AnalysisRequest) -> AnalysisResponse:
        has_image = request.image is not None
        retrieval_request = request
        try:
            if request.image is not None:
                extracted = await self._ai.extract_image(request.image)
                if not isinstance(extracted, str) or not extracted.strip():
                    raise AppError.bad_request("Screenshot contains no readable incident text")
                retrieval_request = request.model_copy(update={
                    "image": None,
                    "description": request.description + "\n" + extracted[:1800],
                })
                request = request.model_copy(update={
                    "image": None,
                    "description": request.description + (
                        "\nBEGIN_UNTRUSTED_SCREENSHOT_OBSERVATIONS\n"
                        + json.dumps(extracted[:1800])
                        + "\nEND_UNTRUSTED_SCREENSHOT_OBSERVATIONS"
                    ),
                })
            embedding = (
                await self._ai.embed(retrieval_request.description)
                if self._settings.retrieval_mode == "legacy"
                else []
            )
            citations = list(
                await self._evidence.search(
                    retrieval_request, embedding, self._settings.max_evidence_items
                )
            )
            context = self._bounded_context(citations)
            included_ids = {
                line.removeprefix("CITATION_ID: ")
                for line in context.splitlines()
                if line.startswith("CITATION_ID: ")
            }
            citations = [citation for citation in citations if citation.id in included_ids]
            if citations:
                output = await self._ai.diagnose(request, context)
            else:
                output = DiagnosisOutput(
                    diagnosis="No sufficiently relevant knowledge matched this incident.",
                    confidence=0,
                    citationIds=[],
                    recommendedHumanActions=[],
                    limitations=[
                        "No grounded diagnosis is available. Supply an error code, "
                        "log message, or a more specific service description."
                    ],
                )
        except (TimeoutError, APITimeoutError) as error:
            raise AppError.timeout(
                "Analysis timed out before a complete response was returned"
            ) from error
        except APIError as error:
            message = (
                "Screenshot analysis failed with the configured AI provider/model. "
                "Verify vision support and configuration, or paste the visible error text."
                if has_image else "AI provider is temporarily unavailable"
            )
            raise AppError.unavailable(message) from error
        except (ValueError, IndexError, TypeError) as error:
            raise AppError.unavailable(
                "AI provider returned an invalid structured diagnosis"
            ) from error
        valid_ids = {citation.id for citation in citations}
        if any(citation_id not in valid_ids for citation_id in output.citation_ids):
            raise AppError.unavailable("Diagnosis cited evidence that was not retrieved")
        selected = [citation for citation in citations if citation.id in output.citation_ids]
        if citations and not selected:
            raise AppError.unavailable("Diagnosis did not cite the supplied evidence")
        limitations = list(output.limitations)
        if has_image:
            limitations.append(
                "Screenshot observations are untrusted model-extracted text, not verified "
                "OCR facts or live telemetry. Confirm visible error details before acting."
            )
        confidence = output.confidence
        if any(citation.source_type == "knowledge" for citation in selected):
            limitations.append(
                "Historical reference examples, not verified live telemetry; "
                "the incident time window does not filter knowledge records."
            )
            if max(citation.relevance or 0 for citation in selected) < 0.1:
                confidence = min(confidence, 0.4)
                limitations.append(
                    "Weak text match; verify the error code and environment before acting."
                )
        response = AnalysisResponse(
            requestId=request_id,
            diagnosis=output.diagnosis,
            confidence=confidence,
            citations=selected,
            recommendedHumanActions=output.recommended_human_actions,
            limitations=limitations,
            prevention=output.prevention,
        )
        await self._analyses.record(
            request_id,
            is_incident=response.confidence > 0 or bool(response.citations),
        )
        return response
