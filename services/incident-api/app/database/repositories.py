import re
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlglot import exp, parse

from app.config import Settings
from app.contracts import (
    AnalysisRequest,
    Citation,
    DashboardMetrics,
    RegisterRequest,
    RequestDataPoint,
)
from app.errors import AppError
from app.models import AnalysisRequestLog, User


class SqlAnalysisRepository:
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def record(self, request_id: str, is_incident: bool) -> None:
        async with self._sessions.begin() as session:
            session.add(AnalysisRequestLog(request_id=request_id, is_incident=is_incident))

    async def metrics(self) -> DashboardMetrics:
        bucket = func.date_trunc("hour", AnalysisRequestLog.created_at).label("bucket")
        async with self._sessions() as session:
            totals = (
                await session.execute(
                    select(
                        func.count(AnalysisRequestLog.id),
                        func.sum(case((AnalysisRequestLog.is_incident, 1), else_=0)),
                    )
                )
            ).one()
            rows = (
                await session.execute(
                    select(bucket, func.count(AnalysisRequestLog.id))
                    .group_by(bucket)
                    .order_by(bucket.desc())
                    .limit(12)
                )
            ).all()
        total = int(totals[0] or 0)
        incidents = int(totals[1] or 0)
        points = [
            RequestDataPoint(label=row[0].strftime("%H:%M"), count=int(row[1]))
            for row in reversed(rows)
        ]
        return DashboardMetrics(
            totalApiRequests=total,
            totalIncidents=incidents,
            totalNonErrors=total - incidents,
            requestsOverTime=points,
        )


class SqlUserRepository:
    def __init__(self, sessions: async_sessionmaker) -> None:
        self._sessions = sessions

    async def get_by_email(self, email: str) -> User | None:
        async with self._sessions() as session:
            result = await session.execute(select(User).where(User.email == email.lower()))
            return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        async with self._sessions() as session:
            return await session.get(User, user_id)

    async def create(self, request: RegisterRequest, password_hash: str) -> User:
        async with self._sessions.begin() as session:
            user = User(
                email=str(request.email).lower(),
                display_name=request.display_name,
                password_hash=password_hash,
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user


class SqlEvidenceRepository:
    _KNOWLEDGE_SQL = """
        WITH query AS (
            SELECT CAST(replace(plainto_tsquery('english', :query)::text,
                                ' & ', ' | ') AS tsquery) AS terms,
                   tsvector_to_array(to_tsvector('english', :query)) AS lexemes
        )
        SELECT id, source_file, row_id, issue_id, metadata,
               ts_rank_cd(search_vector, query.terms, 32) AS relevance
        FROM knowledge_records CROSS JOIN query
        WHERE search_vector @@ query.terms
          AND (CAST(:service AS text) IS NULL OR lower(service) = lower(:service))
          AND ts_rank_cd(search_vector, query.terms, 32) >= :min_score
          AND (
              SELECT count(*) FROM unnest(query.lexemes) AS token
              WHERE token = ANY(tsvector_to_array(search_vector))
          ) >= greatest(2, ceil(cardinality(query.lexemes) * 0.6))
        ORDER BY relevance DESC, id
        LIMIT :limit
    """
    _SEARCH_SQL = """
        SELECT id::text, source_type, source, excerpt, observed_at
        FROM (
            SELECT id, 'runbook' AS source_type, title AS source,
                   LEFT(content, 2000) AS excerpt, NULL::timestamptz AS observed_at,
                   embedding <=> CAST(:embedding AS vector) AS relevance
            FROM runbooks
            WHERE (CAST(:service AS text) IS NULL OR service = CAST(:service AS text))
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:embedding AS vector), id
            LIMIT :limit
        ) runbook_matches
        UNION ALL
        SELECT id::text, source_type, source, excerpt, observed_at
        FROM (
            SELECT id, 'log' AS source_type, source, LEFT(excerpt, 2000) AS excerpt,
                   observed_at
            FROM log_evidence
                        WHERE (CAST(:service AS text) IS NULL OR service = CAST(:service AS text))
                              AND (
                                  CAST(:since AS timestamptz) IS NULL
                                  OR observed_at >= CAST(:since AS timestamptz)
                              )
            ORDER BY observed_at DESC, id
            LIMIT :limit
        ) log_matches
        UNION ALL
        SELECT id::text, source_type, source, excerpt, observed_at
        FROM (
            SELECT id, 'metric' AS source_type, metric_name AS source,
                   LEFT(metric_name || ' = ' || value::text || COALESCE(' ' || unit, ''), 2000)
                       AS excerpt,
                   observed_at
            FROM metric_evidence
                        WHERE (CAST(:service AS text) IS NULL OR service = CAST(:service AS text))
                              AND (
                                  CAST(:since AS timestamptz) IS NULL
                                  OR observed_at >= CAST(:since AS timestamptz)
                              )
            ORDER BY observed_at DESC, id
            LIMIT :limit
        ) metric_matches
        LIMIT :limit
    """

    def __init__(self, sessions: async_sessionmaker, settings: Settings) -> None:
        self._sessions = sessions
        self._settings = settings

    async def search(
        self, request: AnalysisRequest, embedding: Sequence[float], limit: int
    ) -> list[Citation]:
        if self._settings.retrieval_mode == "knowledge":
            self._parse_time_window(request.time_window)
            async with self._sessions() as session:
                await session.execute(text("SET TRANSACTION READ ONLY"))
                rows = (
                    (
                        await session.execute(
                            text(self._KNOWLEDGE_SQL),
                            {
                                "query": request.description,
                                "service": request.service,
                                "limit": min(limit, self._settings.max_evidence_items),
                                "min_score": self._settings.retrieval_min_score,
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                return [
                    Citation(
                        id=row["id"],
                        sourceType="knowledge",
                        source=f"{row['source_file']} / row {row['row_id']} / {row['issue_id']}",
                        rowId=row["row_id"],
                        issueId=row["issue_id"],
                        relevance=float(row["relevance"]),
                        excerpt=self._knowledge_excerpt(row["metadata"]),
                    )
                    for row in rows
                ]
        since = self._parse_time_window(request.time_window)
        vector = "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
        rows = await self._execute_search(
            {
                "service": request.service,
                "since": since,
                "limit": limit,
                "embedding": vector,
            },
        )
        return [
            Citation(
                id=row["id"],
                sourceType=row["source_type"],
                source=row["source"],
                excerpt=row["excerpt"],
                observedAt=row["observed_at"].isoformat() if row["observed_at"] else None,
            )
            for row in rows
        ]

    @staticmethod
    def _knowledge_excerpt(metadata: dict[str, str]) -> str:
        fields = ("root_cause", "solution", "prevention", "error_code", "log_message", "rag_text")
        return "\n".join(f"{field}: {metadata[field][:300]}" for field in fields)[:2000]

    def _parse_time_window(self, value: str | None) -> datetime | None:
        if value is None:
            return datetime.now(UTC) - timedelta(minutes=self._settings.default_lookback_minutes)
        match = re.fullmatch(r"(?:last\s+)?(\d+)\s+(minute|minutes|hour|hours)", value.lower())
        if match is None:
            raise AppError.bad_request(
                "timeWindow must use a format such as 'last 30 minutes' or 'last 2 hours'"
            )
        amount = int(match.group(1))
        delta = (
            timedelta(hours=amount)
            if match.group(2).startswith("hour")
            else timedelta(minutes=amount)
        )
        if amount < 1 or delta > timedelta(days=self._settings.max_lookback_days):
            raise AppError.bad_request(
                f"timeWindow cannot exceed {self._settings.max_lookback_days} days"
            )
        return datetime.now(UTC) - delta

    async def _execute_search(self, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        statement = self._SEARCH_SQL
        try:
            expressions = parse(statement, read="postgres")
        except Exception as error:
            raise AppError.bad_request("Evidence query is not valid PostgreSQL") from error
        if len(expressions) != 1:
            raise AppError.bad_request("Exactly one read-only evidence query is allowed")
        expression = expressions[0]
        write_nodes = (
            exp.Insert,
            exp.Update,
            exp.Delete,
            exp.Create,
            exp.Drop,
            exp.Alter,
            exp.Command,
            exp.Into,
        )
        if expression.find(exp.Select) is None or any(
            expression.find(node) for node in write_nodes
        ):
            raise AppError.bad_request("Only read-only SELECT evidence queries are allowed")
        async with self._sessions() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            result = await session.execute(text(statement), parameters)
            return [dict(row) for row in result.mappings().all()]
