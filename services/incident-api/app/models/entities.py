from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as POSTGRES_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(POSTGRES_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Runbook(Base):
    __tablename__ = "runbooks"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    service: Mapped[str | None] = mapped_column(String(120), index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))


class LogEvidence(Base):
    __tablename__ = "log_evidence"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text)
    service: Mapped[str | None] = mapped_column(String(120), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MetricEvidence(Base):
    __tablename__ = "metric_evidence"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(300))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(40))
    service: Mapped[str | None] = mapped_column(String(120), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AnalysisRequestLog(Base):
    __tablename__ = "analysis_request_logs"

    id: Mapped[UUID] = mapped_column(POSTGRES_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    is_incident: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


Index(
    "ix_runbooks_embedding_hnsw",
    Runbook.embedding,
    postgresql_using="hnsw",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)
