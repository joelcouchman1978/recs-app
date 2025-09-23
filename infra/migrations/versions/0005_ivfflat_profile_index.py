"""create ivfflat index on embeddings_profile.emb_v

Revision ID: 0005_ivfflat_profile_index
Revises: 0004_ivfflat_index
Create Date: 2025-09-21
"""

from alembic import op


revision = '0005_ivfflat_profile_index'
down_revision = '0004_ivfflat_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_profile_emb_v_ivfflat ON embeddings_profile USING ivfflat (emb_v) WITH (lists = 100)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_profile_emb_v_ivfflat")

