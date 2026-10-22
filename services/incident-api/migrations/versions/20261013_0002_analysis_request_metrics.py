"""Add durable analysis request metrics.

Revision ID: 20261013_0002
Revises: 20261013_0001
Create Date: 2026-10-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261013_0002"
down_revision: str | None = "20261013_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_request_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("is_incident", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(
        "ix_analysis_request_logs_request_id",
        "analysis_request_logs",
        ["request_id"],
        unique=True,
    )
    op.create_index(
        "ix_analysis_request_logs_created_at",
        "analysis_request_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_request_logs_created_at", table_name="analysis_request_logs")
    op.drop_index("ix_analysis_request_logs_request_id", table_name="analysis_request_logs")
    op.drop_table("analysis_request_logs")