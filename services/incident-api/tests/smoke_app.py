import json
from dataclasses import replace

from app.contracts import DiagnosisOutput
from app.diagnosis.service import DiagnosisService
from app.main import app
from app.registry import initialize_services, register_services


class MockGroundedAI:
    async def extract_image(self, image) -> str:
        return "Windows VM disk timeout storage errors"

    async def embed(self, text: str) -> list[float]:
        raise RuntimeError("Embeddings are disabled in the smoke backend")

    async def health_check(self) -> bool:
        return True

    async def diagnose(self, request, labeled_context: str) -> DiagnosisOutput:
        record = next(
            json.loads(line.removeprefix("UNTRUSTED_RECORD: "))
            for line in labeled_context.splitlines()
            if line.startswith("UNTRUSTED_RECORD: ")
        )
        fields = dict(
            line.split(": ", 1) for line in record["excerpt"].splitlines() if ": " in line
        )
        return DiagnosisOutput(
            diagnosis=fields.get("root_cause", "Review the cited historical example."),
            confidence=0.65,
            citationIds=[record["id"]],
            recommendedHumanActions=[fields.get("solution", "Review the cited solution.")],
            prevention=[fields.get("prevention", "Review the cited prevention guidance.")],
            limitations=[
                "Mocked GPT and screenshot extraction; no image text was actually read "
                "and no external AI request was made."
            ],
        )


services = initialize_services()
mock_ai = MockGroundedAI()
register_services(
    replace(
        services,
        ai=mock_ai,
        diagnosis=DiagnosisService(
            services.settings, services.evidence, mock_ai, services.analyses
        ),
    )
)

__all__ = ["app"]
