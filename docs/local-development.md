# Local development

## Prerequisites

- Python 3.11 or later
- Docker with Docker Compose
- Node.js and npm for the incident web client

## Configure

Create `.env` from `.env.example`, then replace the local PostgreSQL password and `JWT_SECRET`. Keep `ENVIRONMENT=Development` exactly; any other or missing value selects production managed-identity providers and requires valid Azure configuration.

The local AI provider is deterministic and performs no network calls. Application Insights is optional and falls back safely when unconfigured.

## Run PostgreSQL

```shell
docker compose up -d postgres
```

The Compose service contains no schema migrations and no seed data. The integration phase owns database migrations.

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