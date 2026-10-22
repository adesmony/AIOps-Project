# Integration Plan

## Backend

- Folder: `services/incident-api`
- Install: `python -m pip install -e "services/incident-api[dev]"`
- Build checks: `python -m compileall services/incident-api/app`; `python -m ruff check services/incident-api/app`
- Run: `python -m uvicorn app.main:app --app-dir services/incident-api --port 8000`
- Port: `8000`
- Health: `GET /api/health`
- OpenAPI: `GET /api/openapi.json`; docs at `/api/docs`
- Required local config: root `.env` with exact `ENVIRONMENT=Development`, `DATABASE_URL`, and 32+ character `JWT_SECRET`

## Frontend

- Folder: `services/incident-web`
- Install: `npm --prefix services/incident-web install`
- Build: `npm --prefix services/incident-web run build`
- Test: `npm --prefix services/incident-web test`
- Dev: `npm --prefix services/incident-web run dev`
- API seam: replace mock wiring only in `services/incident-web/src/api/index.js` with a live `ApiClient` implementation using `API_BASE_URL`, `credentials: "include"`, and the JSDoc contract in `src/api/types.js`.
- Response mapping: backend citations use `{ id, sourceType, source, excerpt, observedAt }`; map to the UI seam's `{ id, type, source, evidence, observedAt }`. Backend users use `{ id, displayName, email }`; map `displayName` to UI `name` and assign the UI role label locally.
- Delete after live wiring: `services/incident-web/src/api/mockClient.js` and `services/incident-web/src/api/previewState.js`.
- Remove the dev-only Mock State Switcher and preview-state calls from `services/incident-web/src/app.js` after deleting `previewState.js`.
- No `src/mocks/` folder or duplicated fixture dataset exists.

## API Routes

- `GET /api/health` - public dependency health
- `POST /api/auth/register` - create account
- `POST /api/auth/login` - set signed HttpOnly session cookie
- `POST /api/auth/logout` - clear session cookie
- `GET /api/auth/me` - current authenticated user
- `POST /api/incidents/analyze` - protected cited incident diagnosis

All errors use `{ error: { code, message, details }, requestId }`. The live client must preserve cookie credentials and handle `401` by returning to login.

## Database

- Type: PostgreSQL 16 with pgvector
- Local service: `docker compose up -d postgres`
- Migration tool: Alembic
- Config: `services/incident-api/alembic.ini`
- Migration directory to create: `services/incident-api/migrations`
- Models: `services/incident-api/app/models/entities.py`
- Connection env: local `DATABASE_URL`; production `AZURE_POSTGRES_HOST`, `AZURE_POSTGRES_DATABASE`, `AZURE_POSTGRES_USER` with managed identity
- Required schema: enable `vector`; create `users`, `runbooks`, `log_evidence`, and `metric_evidence`; add the declared HNSW vector index.
- Create migrations only. **NO seed data.**

## Contracts

- Backend canonical Pydantic contracts: `services/incident-api/app/contracts/`
- Frontend typed JSDoc boundary: `services/incident-web/src/api/types.js`
- Vanilla JavaScript has no shared-package import alias; the live client is the contract adapter.

## Services

- Essential: FastAPI/Container Apps runtime, Static Web Apps frontend, PostgreSQL with pgvector, Azure OpenAI chat and embedding deployments, application auth
- Enhancement: Application Insights; retain the safe no-op fallback when unconfigured
- Production Azure access: managed identity only; no database passwords or Azure OpenAI API keys

## Integration Progress (2026-10-13)

- Created an Alembic environment and reversible schema-only revision for `vector`, `users`, `runbooks`, `log_evidence`, and `metric_evidence`; no seed data was created.
- Verified offline PostgreSQL SQL generation for all tables and indexes, including the cosine HNSW vector index.
- Backend compilation and Ruff checks pass. Uvicorn starts, all six API routes register, and endpoint probes return structured `204`/`4xx` responses without runtime `500`s.
- Replaced the frontend mock client with the live cookie-based API adapter, removed mock/preview-state files and controls, configured the Vite proxy, and verified frontend tests and production build.
- Ran frontend and backend concurrently. `GET /` through Vite returned `200`, proxied `GET /api/openapi.json` returned `200`, and the browser rendered the live signed-out state from `/api/auth/me`.
- Applied Alembic revision `20261013_0001` to the local PostgreSQL 16/pgvector service. Verified the `vector` extension, all four domain tables, and the declared indexes, including the cosine HNSW index.
- Re-ran backend smoke tests against the migrated database: health and OpenAPI return `200`; auth and analysis probes return expected `204`/`401`/`422` responses with no runtime `500`s.
- Re-ran frontend and backend concurrently. Vite returned `200` for `/`, proxied `/api/openapi.json` returned `200`, and the browser rendered the live signed-out state from `/api/auth/me`.
- Integration completed successfully against an empty schema; no seed or fixture data was created or run.
- Skill alignment: telemetry retrieval now uses only the fixed repository query template, omitted windows receive a configured default bound, requested windows are capped, focused policy tests pass, and `docs/data-mapping.md` labels the local schema as unverified example infrastructure with production decisions still open.
