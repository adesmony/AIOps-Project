import csv
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.contracts import AnalysisRequest
from app.database.ingest import REQUIRED_COLUMNS, import_csv
from app.database.providers import create_database_provider
from app.database.repositories import SqlEvidenceRepository
from app.diagnosis.providers import DirectOpenAIProvider
from tests.unit.test_images import image_url

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 for local PostgreSQL tests"
)
DATASET = Path(__file__).resolve().parents[4] / "Test_Dataset_azure_windows_error.csv"


@pytest_asyncio.fixture
async def database():
    provider = create_database_provider(get_settings())
    try:
        yield provider
    finally:
        await provider.close()


def write_csv(path, rows, fieldnames=None):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or sorted(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


async def test_ingestion_idempotence_updates_and_savepoint_recovery(database, tmp_path):
    with DATASET.open(encoding="utf-8-sig", newline="") as handle:
        sample = next(csv.DictReader(handle))
    rows = [
        dict(sample, row_id=str(index), issue_id=issue)
        for index, issue in enumerate(["ok-1", "reject", "ok-2"])
    ]
    path = tmp_path / "fixture.csv"
    write_csv(path, rows)
    async with database._engine.connect() as connection:
        async with connection.begin():
            await connection.execute(
                text(
                    "CREATE TEMP TABLE knowledge_records "
                    "(LIKE public.knowledge_records INCLUDING ALL) ON COMMIT DROP"
                )
            )
            await connection.execute(
                text("ALTER TABLE knowledge_records ADD CHECK (issue_id <> 'reject')")
            )
            sessions = async_sessionmaker(connection, join_transaction_mode="create_savepoint")
            first = await import_csv(path, sessions)
            assert (first.imported, first.skipped, first.failed) == (2, 0, 1)
            second = await import_csv(path, sessions)
            assert (second.imported, second.skipped, second.failed) == (0, 2, 1)
            rows[0]["solution"] = "Updated operator review"
            write_csv(path, rows)
            updated = await import_csv(path, sessions)
            assert (updated.imported, updated.skipped, updated.failed) == (1, 1, 1)
            malformed = tmp_path / "malformed.csv"
            write_csv(malformed, [dict(sample, rag_text="")])
            assert (await import_csv(malformed, sessions)).failed == 1


async def test_missing_columns_fail_before_writes(database, tmp_path):
    path = tmp_path / "invalid.csv"
    write_csv(path, [{"row_id": "1"}], ["row_id"])
    with pytest.raises(ValueError, match="Missing required CSV columns"):
        await import_csv(path, database.session_factory)


async def test_real_dataset_retrieval_provenance_filters_and_no_match(database):
    repository = SqlEvidenceRepository(database.session_factory, get_settings())
    async with database.session() as session:
        count = await session.scalar(text("SELECT count(*) FROM knowledge_records"))
        sample = (
            await session.execute(
                text("SELECT metadata FROM knowledge_records ORDER BY row_id LIMIT 1")
            )
        ).scalar_one()
    assert count == 1000
    query = f"{sample['error_code']} {sample['log_message']}"
    citations = await repository.search(
        AnalysisRequest(description=query, service=sample["azure_service"]), [], 3
    )
    assert 1 <= len(citations) <= 3
    assert all(
        citation.row_id and citation.issue_id and citation.relevance for citation in citations
    )
    assert any(citation.issue_id == sample["issue_id"] for citation in citations)
    assert all(
        "root_cause:" in citation.excerpt and "prevention:" in citation.excerpt
        for citation in citations
    )
    assert not await repository.search(
        AnalysisRequest(description="zzzzunknownxyz qqqqnomatch"), [], 3
    )
    assert not await repository.search(
        AnalysisRequest(description="zzzzunknownxyz qqqqnomatch preferences check"), [], 3
    )
    assert not await repository.search(
        AnalysisRequest(description=query, service="nonexistent-service"), [], 3
    )
    print(
        f"SMOKE retrieval: count={count}; error={sample['error_code']}; "
        f"service={sample['azure_service']}; citations="
        + json.dumps(
            [
                {"rowId": item.row_id, "issueId": item.issue_id, "score": item.relevance}
                for item in citations
            ]
        )
    )


async def test_retrieval_transaction_rejects_writes(database, monkeypatch):
    repository = SqlEvidenceRepository(database.session_factory, get_settings())
    monkeypatch.setattr(repository, "_KNOWLEDGE_SQL", "DELETE FROM knowledge_records RETURNING id")
    with pytest.raises(DBAPIError, match="read-only"):
        await repository.search(AnalysisRequest(description="timeout error occurred"), [], 3)


async def test_authenticated_api_real_records_mocked_gpt(database, monkeypatch):
    from app.dependencies import services_dependency
    from app.main import app
    from app.registry import initialize_services

    services = initialize_services()
    completion = AsyncMock()
    async with database.session() as session:
        screenshot_record = (
            await session.execute(
                text("SELECT metadata FROM knowledge_records ORDER BY row_id LIMIT 1")
            )
        ).scalar_one()

    async def complete(**kwargs):
        if isinstance(kwargs["messages"][1]["content"], list):
            assert kwargs["messages"][1]["content"][1]["type"] == "image_url"
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"text": (
                    f"{screenshot_record['error_code']} {screenshot_record['log_message']}"
                )})
            ))])
        payload = json.loads(kwargs["messages"][1]["content"])
        assert "image" not in payload["incident"]
        context = payload["untrusted_evidence"]
        identifier = next(
            line.removeprefix("CITATION_ID: ")
            for line in context.splitlines()
            if line.startswith("CITATION_ID: ")
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "diagnosis": (
                                    "Historical reference suggests checking "
                                    "the cited Windows error condition."
                                ),
                                "confidence": 0.7,
                                "citationIds": [identifier],
                                "recommendedHumanActions": [
                                    "Compare the cited log and solution with the affected host."
                                ],
                                "prevention": ["Review the cited prevention guidance."],
                                "limitations": ["Mocked GPT; no live environment was inspected."],
                            }
                        )
                    )
                )
            ]
        )

    completion.side_effect = complete
    monkeypatch.setattr(
        "app.diagnosis.providers.AsyncOpenAI",
        lambda **kwargs: SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completion))
        ),
    )
    configured = get_settings().model_copy(
        update={"gpt_model_api_key": SecretStr("test-only-key")}
    )
    provider = DirectOpenAIProvider(configured)
    services.diagnosis._ai = provider
    app.dependency_overrides[services_dependency] = lambda: services
    email = f"smoke-{uuid4().hex}@example.com"
    request_ids = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (
                await client.post(
                    "/api/incidents/analyze", json={"description": "Timeout error occurred"}
                )
            ).status_code == 401
            credentials = {"email": email, "password": "Local-smoke-test-password-123"}
            assert (
                await client.post(
                    "/api/auth/register", json=credentials | {"displayName": "CSV smoke"}
                )
            ).status_code == 201
            assert (await client.post("/api/auth/login", json=credentials)).status_code == 200
            before = (await client.get("/api/incidents/metrics")).json()
            response = await client.post(
                "/api/incidents/analyze",
                json={
                    "description": "Windows VM reports disk timeout and storage errors",
                    "timeWindow": "Last 2 hours",
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            request_ids.append(body["requestId"])
            assert body["citations"] and body["citations"][0]["rowId"]
            assert body["prevention"] and body["recommendedHumanActions"] and body["limitations"]
            assert completion.await_count == 1
            screenshot = await client.post(
                "/api/incidents/analyze", json={
                    "description": "Inspect attached screenshot",
                    "image": {"dataUrl": image_url()},
                    "userType": "developer", "responseStyle": "detailed",
                },
            )
            assert screenshot.status_code == 200, screenshot.text
            screenshot_body = screenshot.json()
            request_ids.append(screenshot_body["requestId"])
            assert screenshot_body["citations"][0]["rowId"]
            assert any(item["issueId"] == screenshot_record["issue_id"]
                       for item in screenshot_body["citations"])
            assert any("Screenshot observations" in item
                       for item in screenshot_body["limitations"])
            assert completion.await_count == 3
            unsafe_image = await client.post(
                "/api/incidents/analyze", json={
                    "description": "Inspect screenshot error",
                    "image": {"dataUrl": "data:image/svg+xml;base64,PHN2Zy8+"},
                },
            )
            assert unsafe_image.status_code == 422
            assert "PHN2Zy8+" not in unsafe_image.text
            assert completion.await_count == 3
            no_match = await client.post(
                "/api/incidents/analyze", json={"description": "zzzzunknownxyz qqqqnomatch"}
            )
            assert no_match.status_code == 200
            request_ids.append(no_match.json()["requestId"])
            assert no_match.json()["confidence"] == 0
            assert completion.await_count == 3
            invalid = await client.post(
                "/api/incidents/analyze", json={"description": "short", "attachment": {"bad": True}}
            )
            assert invalid.status_code == 422
            after = (await client.get("/api/incidents/metrics")).json()
            assert after["totalApiRequests"] == before["totalApiRequests"] + 3
            assert after["totalIncidents"] == before["totalIncidents"] + 2
            assert after["totalNonErrors"] == before["totalNonErrors"] + 1
            assert (await client.post("/api/auth/logout")).status_code == 204
            print(
                "SMOKE API: auth=401/register=201/login=200/analyze=200/"
                "no-match=200/invalid=422/logout=204; "
                f"GPT mock calls={completion.await_count}; "
                f"citation row={body['citations'][0]['rowId']}; "
                f"issue={body['citations'][0]['issueId']}; counters delta=3/2/1"
            )
    finally:
        app.dependency_overrides.clear()
        async with database.session_factory.begin() as session:
            await session.execute(text("DELETE FROM users WHERE email=:email"), {"email": email})
            for request_id in request_ids:
                await session.execute(
                    text("DELETE FROM analysis_request_logs WHERE request_id=:id"),
                    {"id": request_id},
                )
        await services.database.close()
