"""add pgvector columns to embeddings tables

Revision ID: 0003_pgvector_columns
Revises: 0002_availability_unique_upsert
Create Date: 2025-09-21
"""

from alembic import op


revision = '0003_pgvector_columns'
down_revision = '0002_availability_unique_upsert'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("ALTER TABLE embeddings_show ADD COLUMN IF NOT EXISTS emb_v vector(384)")
    op.execute("ALTER TABLE embeddings_profile ADD COLUMN IF NOT EXISTS emb_v vector(384)")


def downgrade() -> None:
    op.execute("ALTER TABLE embeddings_profile DROP COLUMN IF EXISTS emb_v")
    op.execute("ALTER TABLE embeddings_show DROP COLUMN IF EXISTS emb_v")

