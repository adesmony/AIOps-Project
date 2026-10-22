# Project Plan

**Status**: Integrated
**Created**: 2026-10-13
**Mode**: NEW
**Execution Mode**: auto

---

## 1. Project Overview

**Goal**: Build a read-only, human-in-the-loop incident analysis chatbot that retrieves cited runbooks and operational evidence, produces a structured AI-assisted diagnosis, and clearly separates recommendations from actions that an operator must review and perform. The project is designed so that every module is independently testable.

**App Type**: SPA + API

**API Login**: Yes

**Mode**: NEW

**Deployment Plan**: No deployment plan found

---

## 2. Incident Analysis API — Backend

| Component | Technology |
|-----------|-----------|
| **Language** | Python |
| **Framework** | FastAPI |
| **Runtime** | CPython |
| **Package Manager** | pip |
| **Data Access** | SQLAlchemy async + asyncpg + pgvector |
| **AI Integration** | Azure OpenAI, configurable deployment with `azure/gpt-4.1` documented as the default |
| **Test Runner** | pytest |
| **Mocking Library** | unittest.mock |
| **Test Command** | `python -m pytest` |
| **Orchestration** | docker-compose |

The API accepts incident context and optional service/time-window filters, performs deterministic vector retrieval and parameterized read-only evidence queries, bounds and labels all model context, and returns a structured diagnosis with confidence, request ID, citations, and recommended human actions. It must reject write SQL, avoid secrets and sensitive payloads in telemetry, apply timeouts and bounded retries, and expose no remediation or Azure mutation capability.

---

## 3. Incident Chat Interface — Frontend

| Component | Technology |
|-----------|-----------|
| **Language** | JavaScript |
| **Framework** | Vanilla JavaScript |
| **Package Manager** | npm |
| **Test Runner** | vitest |
| **Mocking Library** | vi.mock |
| **Test Command** | `npm test` |

The browser client provides incident input, service and time filters, explicit loading/error/empty states, request ID visibility, structured diagnosis and confidence, inspectable runbook/log/metric citations, and a visually separate “Recommended human actions” area. No copy, status, or control may imply that remediation was executed.

---

## 4. Services Required

| Azure Service | Role in App | Environment Variable | Default Value (Local) | Classification |
|---------------|------------|---------------------|----------------------|----------------|
| Azure Container Apps | Host the FastAPI incident analysis API | `PORT` | `8000` | Essential |
| Azure Static Web Apps | Host the vanilla JavaScript incident chat interface | `API_BASE_URL` | `http://localhost:8000` | Essential |
| Azure Database for PostgreSQL Flexible Server with pgvector | Store runbooks, embeddings, logs, metrics, and citation metadata for read-only retrieval | `DATABASE_URL` | `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/aiops` | Essential |
| Azure OpenAI | Generate the structured diagnosis and recommended human actions from bounded cited context | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` | Endpoint unconfigured; deployment `azure/gpt-4.1` | Essential |
| Application Insights | Capture non-sensitive request, latency, dependency, retry, and failure telemetry | `APPLICATIONINSIGHTS_CONNECTION_STRING` | Unconfigured | Enhancement |

---

## 5. Prerequisites

### Run

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Python | Incident Analysis API | ❓ | Unconfirmed |
| pip | Incident Analysis API | ❓ | Unconfirmed |
| Node.js | Incident Chat Interface | ❓ | Unconfirmed |
| npm | Incident Chat Interface | ❓ | Unconfirmed |

### Debug

| Tool | Service(s) | Installed | Version |
|------|------------|-----------|---------|
| Docker | Incident Analysis API | ❓ | Unconfirmed |
| Docker Compose | Incident Analysis API | ❓ | Unconfirmed |
| Microsoft Edge | Incident Chat Interface | ✅ | 155.0.4283.45 |

Double-check every tool marked ❓ before running or debugging the project.

---

## 6. Design System & UI

**Component Library**: Pico.css
**Style Direction**: A quiet, data-dense operations console with crisp 4px corners, restrained elevation, strong evidence hierarchy, and amber accents reserved for recommendations that require human review. Diagnosis, evidence, and recommendations remain visually distinct so the interface never suggests an action was executed.
**Typography**: Segoe UI Variable, system-ui

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `primary` | `#0F6CBD` | Analyze command, active evidence tabs, citation links, and keyboard focus |
| `accent` | `#CA5010` | Human-review recommendation labels and caution highlights |
| `surface` | `#F7F8FA` | Incident workspace and evidence-reading background |
| `text` | `#17212B` | Diagnosis, evidence excerpts, form labels, and body text |
| `muted` | `#56616F` | Request IDs, timestamps, source metadata, and secondary context |
| `border` | `#C7CED8` | Form fields, evidence rows, separators, and bounded result panels |

### Pages

| Page | Route | Purpose | Layout |
|------|-------|---------|--------|
| Incident Analysis | `/` | Submit incident context and inspect the resulting diagnosis, confidence, citations, and recommended human actions in one operational workspace | `header, main, split(form|tabs), action-bar, footer` |

### Sample Content

Incident Analysis — representative diagnoses:

| Incident | Service / Window | Diagnosis | Confidence | Review State |
|----------|------------------|-----------|------------|--------------|
| Checkout requests exceed the 2 s SLO | `checkout-api` / last 30 minutes | PostgreSQL connection-pool saturation is queuing requests during traffic bursts | 0.87 | Human review required |
| Duplicate payment events after worker restarts | `payments-worker` / last 2 hours | Message processing exceeds the lock-renewal window and redelivers in-flight events | 0.79 | Human review required |
| Product detail requests return intermittent 503s | `catalog-api` / last 45 minutes | Recent configuration drift reduced healthy upstream endpoints below expected capacity | 0.72 | Human review required |

Incident Analysis — cited evidence:

| Citation | Source Type | Source | Evidence |
|----------|-------------|--------|----------|
| `RB-042` | Runbook | Database connection saturation | Compare active connections with pool limits before adjusting capacity |
| `LOG-7841` | Log | `checkout-api` | `pool timeout after 3000 ms; 48 waiters` at 14:26 UTC |
| `METRIC-218` | Metric | `db.pool.waiting` | Increased from 3 to 48 while p95 latency reached 4.8 s |
| `RB-017` | Runbook | Message lock renewal | Verify handler duration and renewal failures before replaying messages |

Incident Analysis — defaults and states: Incident description: “Checkout latency increased after the 14:00 release” · Service filter: `checkout-api` · Time window: Last 30 minutes · Empty state: no evidence matched the selected service/window · Loading state: retrieving runbooks and operational evidence · Error state: analysis timed out before Azure OpenAI returned a complete structured response · Recommendation label: “Recommended human actions — not executed.”

---

## 7. Project Structure

```text
AIOps/
├── .azure/
│   └── project-plan.md
├── .env.example
├── .gitignore
├── compose.yaml
├── services/
│   ├── incident-api/
│   │   ├── pyproject.toml
│   │   ├── alembic.ini
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/
│   │   │   │   ├── health.py
│   │   │   │   └── incidents.py
│   │   │   ├── contracts/
│   │   │   ├── retrieval/
│   │   │   ├── evidence/
│   │   │   ├── diagnosis/
│   │   │   ├── telemetry/
│   │   │   └── config.py
│   │   ├── migrations/
│   │   ├── seeds/
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       └── fixtures/
│   └── incident-web/
│       ├── package.json
│       ├── index.html
│       ├── src/
│       │   ├── api.js
│       │   ├── app.js
│       │   ├── render.js
│       │   └── styles.css
│       └── tests/
└── docs/
    └── local-development.md
```

---

## 8. Route Definitions

| # | Method | Path | Description | Request Body | Response Body | Status Codes |
|---|--------|------|-------------|-------------|--------------|-------------|
| 1 | GET | `/api/health` | Report API and required dependency health without exposing secrets | — | `{ status, services }` | 200, 503 |
| 2 | POST | `/api/incidents/analyze` | Retrieve bounded cited evidence and generate a structured, read-only incident diagnosis | `{ description, service?, timeWindow? }` | `{ requestId, diagnosis, confidence, citations[], recommendedHumanActions[], limitations[] }` | 200, 400, 422, 500, 503, 504 |

All errors use `{ "error": { "code": "...", "message": "...", "details": null }, "requestId": "..." }`. The API exposes no remediation, command execution, write-query, or Azure mutation route.

---

## 9. Next Steps

1. Run **azure-project-scaffold** to execute this plan
2. Run **azure-project-integrate** to wire the frontend to live data, smoke-test the backend, and create the migrations
3. Run **azure-debug-plan** → **azure-debug-generate** for Docker emulators and VS Code debugging
4. Run the **azure-deploy** agent when ready; it uses **azure-app-onboard** for architecture, cost estimation, IaC generation, provisioning, and health verification