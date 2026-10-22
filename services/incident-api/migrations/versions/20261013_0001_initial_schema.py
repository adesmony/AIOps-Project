"""Create the initial incident analysis schema.

Revision ID: 20261013_0001
Revises:
Create Date: 2026-10-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20261013_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "runbooks",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("service", sa.String(length=120), nullable=True),
        sa.Column("embedding", Vector(dim=1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runbooks_service", "runbooks", ["service"], unique=False)
    op.create_index(
        "ix_runbooks_embedding_hnsw",
        "runbooks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "log_evidence",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=300), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("service", sa.String(length=120), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_evidence_service", "log_evidence", ["service"], unique=False)
    op.create_index(
        "ix_log_evidence_observed_at", "log_evidence", ["observed_at"], unique=False
    )

    op.create_table(
        "metric_evidence",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("metric_name", sa.String(length=300), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("service", sa.String(length=120), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_metric_evidence_service", "metric_evidence", ["service"], unique=False
    )
    op.create_index(
        "ix_metric_evidence_observed_at", "metric_evidence", ["observed_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_metric_evidence_observed_at", table_name="metric_evidence")
    op.drop_index("ix_metric_evidence_service", table_name="metric_evidence")
    op.drop_table("metric_evidence")
    op.drop_index("ix_log_evidence_observed_at", table_name="log_evidence")
    op.drop_index("ix_log_evidence_service", table_name="log_evidence")
    op.drop_table("log_evidence")
    op.drop_index("ix_runbooks_embedding_hnsw", table_name="runbooks")
    op.drop_index("ix_runbooks_service", table_name="runbooks")
    op.drop_table("runbooks")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
