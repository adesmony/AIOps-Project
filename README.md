# Incident Analysis

FastAPI, PostgreSQL full-text retrieval, and a Vite incident workspace. CSV knowledge
is retrieved locally; only bounded evidence and incident text are sent to OpenAI for
structured diagnosis. No embeddings, internet search, or remediation execution are used.
Existing authentication, history, preferences, themes, attachments, and metrics remain.

## Local Setup (PowerShell)

Requirements: Python 3.11+, Node.js/npm, Docker Desktop with Compose. From the repository root:

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e "services/incident-api[dev]"
npm --prefix services/incident-web ci
```

Do not overwrite an existing `.env`. Set its local database credentials and a random
`JWT_SECRET` of at least 32 characters. Keep `ENVIRONMENT=Development`.
For direct OpenAI set `AI_PROVIDER=openai`, `GPT_MODEL_API_KEY` to your key, and
`GPT_MODEL` to an available model ID supporting JSON output, e.g. `gpt-4.1-mini`.
`GPT_MODEL=OpenAI` is a provider label, not a model ID. Keys never belong in frontend
variables. `.env` is ignored. Settings load this root file regardless of working directory.
`AI_PROVIDER=local` runs offline; `auto` selects OpenAI only when a local key is set.
OpenAI health is a configuration check, not a paid call or a credential/model verification.

```powershell
docker compose up -d postgres
pwsh -NoProfile -File .vscode/migrate-db.ps1
python -m app.database.ingest ./Test_Dataset_azure_windows_error.csv
python -m app.database.ingest ./Test_Dataset_azure_windows_error.csv
python -m uvicorn app.main:app --reload --port 8000
```

In another activated terminal:

```powershell
npm --prefix services/incident-web run dev
```

Open http://localhost:5173 and create an account/sign in. API documentation:
http://localhost:8000/api/docs. Restart the API after changing environment settings.
VS Code's existing `debug-all-services: start` task also starts the local services.

## Import and Retrieval

The CLI is an authorized local administrative operation, not an HTTP upload route.
Use database credentials with write permission only for migrations/import. All 19 CSV
headers are required; nonempty values and a maximum 30,000-character `rag_text` are
validated per row. A source filename plus `row_id` identifies a record; identical rows
skip, changed rows update. Keep the filename stable for repeat imports.
Each row has a savepoint: malformed or rejected rows increment `failed` while other
rows can commit. A file/connection/outer-transaction failure aborts the whole import
and prints a generic error instead of misleading success counts. A nonzero exit code
indicates failure. Successful output is `{ "imported": N, "skipped": N, "failed": N }`.

`rag_text` is the indexed retrieval document; the complete row is retained as JSONB.
PostgreSQL English full-text search ORs stemmed query terms and ranks matches with
`ts_rank_cd`. `MAX_EVIDENCE_ITEMS` controls top-k; `RETRIEVAL_MIN_SCORE` rejects weak
results. Service filters match case-insensitively and exactly. Lexical retrieval is
required to share at least two distinct stemmed terms and 60% of query terms; isolated
generic-word hits abstain rather than producing unrelated recommendations. Queries
containing only one meaningful term must be expanded with an error code or symptom.
Lexical retrieval is
not semantic understanding: synonyms, negation and misleading shared terms can miss
or misrank evidence. Matches below 0.1 cap reported confidence at 0.4. Scores are not
calibrated probabilities. No match skips GPT and returns zero confidence plus limitations.

Knowledge is historical reference, not live telemetry. Time windows are validated but
do not filter reference records. Citations retain filename, `rowId`, `issueId`, and score.
The prompt includes bounded root cause, solution, prevention, error, log, and `rag_text`
snippets. `MAX_EVIDENCE_CHARS` bounds the complete labeled context. JSON escaping and
system instructions treat evidence and attachments as untrusted. Output schema and
citation IDs are validated; prompt injection resistance is not a guarantee of correctness.
Operators must verify all proposed actions. Only actually prompted evidence can be cited.

Evidence sessions use a PostgreSQL read-only transaction. Diagnosis cannot mutate the
knowledge base or execute remediation. Existing auth and analysis-audit writes are
preserved for sessions and dashboard counters. For additional defense, provision a
dedicated database role with SELECT-only access to knowledge and operational evidence
and narrowly scoped privileges on users/audit tables. The importer needs a separate
administrative credential when using that role.

The legacy runbook/log/metric path remains available with `RETRIEVAL_MODE=legacy` and
the existing providers. Direct OpenAI requires `RETRIEVAL_MODE=knowledge` and never
calls an embeddings API. Existing managed-identity provider behavior is otherwise retained.

## Validation (No Paid Calls)

After migrating and importing the real CSV:

```powershell
python -m pytest services/incident-api/tests/unit -q
$env:RUN_DB_TESTS = '1'
python -m pytest services/incident-api/tests -q -s
python -m ruff check services/incident-api/app services/incident-api/tests services/incident-api/migrations/versions/20261022_0003_knowledge_records.py
python -m compileall -q services/incident-api/app services/incident-api/tests
npm --prefix services/incident-web test
npm --prefix services/incident-web run build
```

Database tests require the imported 1,000-row dataset. They check imports, changed-row
updates, savepoint recovery, retrieval/provenance, read-only enforcement, real auth and
counters, safe errors, and mocked OpenAI. Temporary records are isolated or cleaned up.
There is no configured standalone typecheck or frontend lint script; editor diagnostics,
Ruff, pytest, Vitest and Vite build provide the configured checks.

## End-to-End Example

For an entirely offline GPT smoke backend, start this instead of the normal API:

```powershell
python -m uvicorn tests.smoke_app:app --app-dir services/incident-api --port 8000
```

Use an unused port if 8000 is already occupied; the frontend proxy targets 8000 by
default. For an isolated smoke pair with the backend on port 8001:

```powershell
python -m uvicorn tests.smoke_app:app --app-dir services/incident-api --port 8001
```

In another terminal:

```powershell
$env:API_PROXY_TARGET = 'http://127.0.0.1:8001'
npm --prefix services/incident-web run dev -- --port 5174
```

The smoke module still uses real PostgreSQL/auth/retrieval/audits but replaces
all AI operations. Never deploy this test module as the production application.
In Chat, submit `Windows VM reports disk timeout and storage errors`. Expected:
cited historical rows, human actions, prevention, limitations, and updated counters.
Expand Cited evidence to inspect filename/row/issue provenance. Submit
`zzzzunknownxyz qqqqnomatch` to check abstention with no GPT call. Text/JSON reports are
validated client-side and bounded to 2,500 characters; files over 2 MB, malformed JSON,
invalid UTF-8 and binary/empty text are rejected. Images retain their text-only notice.
Attachments provide request context only; they never ingest into the knowledge base.

With the normal OpenAI backend, the same matched request is a **paid live call**.
Credential validity, model access, live latency and model answer quality require an
explicit live check; automated tests mock these calls. Review sensitive incident and
attachment content before sending it to any external model provider.