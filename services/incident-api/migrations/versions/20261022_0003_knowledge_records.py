from alembic import op

revision = "20261022_0003"
down_revision = "20261013_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE knowledge_records (
            id text PRIMARY KEY,
            source_file text NOT NULL,
            row_id text NOT NULL,
            issue_id text NOT NULL,
            service text NOT NULL,
            rag_text text NOT NULL,
            metadata jsonb NOT NULL,
            fingerprint text NOT NULL,
            search_vector tsvector GENERATED ALWAYS AS (
                to_tsvector('english', rag_text)
            ) STORED,
            UNIQUE (source_file, row_id)
        )
    """)
    op.execute("CREATE INDEX ix_knowledge_search ON knowledge_records USING gin(search_vector)")
    op.execute("CREATE INDEX ix_knowledge_service ON knowledge_records(service)")


def downgrade() -> None:
    op.drop_table("knowledge_records")
