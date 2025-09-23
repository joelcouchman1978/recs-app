"""create ivfflat index on embeddings_show.emb_v

Revision ID: 0004_ivfflat_index
Revises: 0003_pgvector_columns
Create Date: 2025-09-21
"""

from alembic import op


revision = '0004_ivfflat_index'
down_revision = '0003_pgvector_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # Create IVFFLAT index for approximate nearest neighbors
    # Lists=100 is a reasonable default for small datasets; tune as needed
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_show_emb_v_ivfflat ON embeddings_show USING ivfflat (emb_v) WITH (lists = 100)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_show_emb_v_ivfflat")

