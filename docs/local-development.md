# Local development

## Prerequisites

- Python 3.11 or later
- Docker with Docker Compose
- Node.js and npm for the incident web client

## Configure

Create `.env` from `.env.example`, then replace the local PostgreSQL password and `JWT_SECRET`. Keep `ENVIRONMENT=Development` exactly; any other or missing value selects production managed-identity providers and requires valid Azure configuration.

Set `AI_PROVIDER=local` for deterministic offline generation. With `AI_PROVIDER=auto`,
a configured `GPT_MODEL_API_KEY` selects direct OpenAI in Development. Set `GPT_MODEL`
to a real model ID, not the provider label `OpenAI`. Application Insights is optional.
See [README.md](../README.md) for the complete CSV ingestion and no-paid-call workflow.

## Screenshot analysis

Chat sends one optional `image: { dataUrl: "data:image/png;base64,..." }` with the
existing authenticated analysis request. JPEG is also accepted. The server checks
strict base64, MIME/signature agreement, full Pillow decoding, a 2 MB decoded-byte
limit, a 16 megapixel limit, and single-frame raster content. SVG, remote URLs,
unsupported formats, malformed images, and animated images are rejected.

Direct OpenAI extracts up to 1800 characters of visible incident text using SDK
multimodal messages and the exact configured `GPT_MODEL`; it does not select or
verify model availability. This requires that model and account to support image
input and JSON output. Unsupported models, missing configuration, timeouts, and
unreadable screenshots produce safe errors; paste visible error text as a fallback.
Offline and managed-identity providers do not fabricate image observations.

Extracted text enters the existing parameterized read-only retrieval path and is
JSON-escaped inside explicit untrusted screenshot delimiters for diagnosis. Images
are not citations, verified OCR facts, or live telemetry. Retrieved records retain
their row/issue provenance and citation validation. Raw image bytes are excluded
from diagnosis serialization and are not stored by the analysis recorder. Images
are sent to OpenAI for extraction; avoid uploading sensitive screenshots. No image
code or remediation is executed. Text attachments and role/style preferences are
unchanged.

All automated image tests mock OpenAI; they make no paid model calls. With local
PostgreSQL running and the dataset imported, run:

```powershell
$env:RUN_DB_TESTS = '1'
python -m pytest services/incident-api/tests -q
npm --prefix services/incident-web test
npm --prefix services/incident-web run build
python -m ruff check services/incident-api/app services/incident-api/tests
```

The separate `tests.smoke_app:app` preview deliberately returns fixed, labeled
mock screenshot observations. It proves UI transport only, not recognition accuracy.

## Run PostgreSQL

```shell
docker compose up -d postgres
```

The Compose service contains no schema migrations and no seed data. Run migrations
and the CSV importer explicitly:

```powershell
pwsh -NoProfile -File .vscode/migrate-db.ps1
python -m app.database.ingest ./Test_Dataset_azure_windows_error.csv
```

## Install and run the API

Create the virtual environment and install the API package:

```shell
python -m venv services/incident-api/.venv
python -m pip install -e "services/incident-api[dev]"
```

Run from the repository root so Pydantic loads the root `.env` file:

```shell
python -m uvicorn app.main:app --app-dir services/incident-api --reload --port 8000
```

OpenAPI documentation is available at `http://localhost:8000/api/docs`. Health is available at `http://localhost:8000/api/health`.

## Quality checks

From the repository root:

```shell
python -m compileall services/incident-api/app
python -m ruff check services/incident-api/app
```

## Production provider requirements

Production and any environment other than exact `Development` use managed identity for Azure Database for PostgreSQL and Azure OpenAI. Configure `AZURE_POSTGRES_HOST`, `AZURE_POSTGRES_DATABASE`, `AZURE_POSTGRES_USER`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, and `JWT_SECRET`. No database password or Azure OpenAI API key is accepted by the production providers.