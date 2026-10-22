## CSV Reference Knowledge

The local CLI `python -m app.database.ingest ./Test_Dataset_azure_windows_error.csv`
maps the dataset to `knowledge_records`. `rag_text` is the primary full-text document.
The source filename and `row_id` form a stable identity; a SHA-256 fingerprint detects
unchanged rows. The complete source row is retained as JSONB metadata. `issue_id` and
`azure_service` are stored explicitly for provenance and service filtering. A generated
English `tsvector` has a GIN index. No embedding service is involved.

Diagnosis returns `sourceType=knowledge` citations with filename, row and issue IDs,
relevance score, and bounded root cause/solution/prevention/error/log/document text.
Historical reference rows are not constrained by incident time-window filters.
Only the administrative CLI writes knowledge. Evidence retrieval uses read-only
transactions; user/session and analysis-counter writes remain separate.
See [README.md](../README.md) for exact setup, migration, import and validation commands.

# PostgreSQL data mapping

## Status

The current schema is a scaffolded local example, not a verified mapping of a production Azure telemetry database. Production table/view names, approved columns, timestamp semantics, ingestion delay, retention, and authorization scope remain owner decisions.

Do not claim that this schema matches a production source until the data owner supplies and approves a data dictionary.

## Current example schema

| Application concept | Local table | Columns used | Time semantics |
| --- | --- | --- | --- |
| Runbook passage | `runbooks` | `id`, `title`, `content`, `service`, `embedding` | No revision timestamp is currently available |
| Log evidence | `log_evidence` | `id`, `source`, `excerpt`, `service`, `observed_at` | `observed_at` is expected to be UTC with timezone |
| Metric evidence | `metric_evidence` | `id`, `metric_name`, `value`, `unit`, `service`, `observed_at` | `observed_at` is expected to be UTC with timezone |

The `users` table supports application authentication and is not an operational telemetry source.

## Approved query template

`SqlEvidenceRepository._SEARCH_SQL` is the only runtime evidence query template. It:

- uses bound parameters for service, time boundary, embedding, and row limit;
- reads only the three example evidence tables;
- limits each source and the combined result;
- applies service filters to every source and time filters to logs and metrics;
- performs cosine-distance runbook retrieval through pgvector.

The configured `DEFAULT_LOOKBACK_MINUTES` bounds omitted time windows, and `MAX_LOOKBACK_DAYS` caps user-selected windows. No model output is accepted as SQL.

## Production decisions required

- Confirm curated PostgreSQL views and approved columns for Azure logs and metrics.
- Confirm event-time and ingestion-time columns, timezone handling, freshness, and retention.
- Confirm permitted services, environments, regions, metrics, severities, and row limits.
- Provision a dedicated runtime role with `SELECT` only on approved views and prove write/DDL attempts fail.
- Use separate privileged credentials for Alembic migrations and any approved ingestion process.
- Decide whether pgvector and the configured embedding model are approved.