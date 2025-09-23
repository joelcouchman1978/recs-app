"""add offers and serializd history tables

Revision ID: 0006_offers_history
Revises: 0005_ivfflat_profile_index
Create Date: 2025-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = '0006_offers_history'
down_revision = '0005_ivfflat_profile_index'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "justwatch_offers",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("title_ref", sa.Text, nullable=False),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("offer_type", sa.Text, nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("region", sa.String(8), nullable=False, server_default="AU"),
        sa.Column("last_checked_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("raw", sa.JSON, nullable=True),
    )
    op.create_unique_constraint("uq_offers_title_provider_type", "justwatch_offers", ["title_ref", "provider", "offer_type"])
    op.create_index("ix_offers_title", "justwatch_offers", ["title_ref"]) 
    op.create_index("ix_offers_provider", "justwatch_offers", ["provider"]) 
    op.create_index("ix_offers_last_checked", "justwatch_offers", ["last_checked_ts"]) 

    op.create_table(
        "serializd_history",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("profile_ref", sa.Text, nullable=False),
        sa.Column("title_ref", sa.Text, nullable=True),
        sa.Column("tmdb_id", sa.BigInteger, nullable=True),
        sa.Column("season", sa.Integer, nullable=True),
        sa.Column("episode", sa.Integer, nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("rating", sa.SmallInteger, nullable=True),
        sa.Column("last_seen_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("raw", sa.JSON, nullable=True),
    )
    op.create_index("ix_hist_profile_lastseen", "serializd_history", ["profile_ref", "last_seen_ts"]) 
    op.create_index("ix_hist_tmdb", "serializd_history", ["tmdb_id"]) 


def downgrade() -> None:
    op.drop_index("ix_hist_tmdb", table_name="serializd_history")
    op.drop_index("ix_hist_profile_lastseen", table_name="serializd_history")
    op.drop_table("serializd_history")
    op.drop_index("ix_offers_last_checked", table_name="justwatch_offers")
    op.drop_index("ix_offers_provider", table_name="justwatch_offers")
    op.drop_index("ix_offers_title", table_name="justwatch_offers")
    op.drop_constraint("uq_offers_title_provider_type", "justwatch_offers")
    op.drop_table("justwatch_offers")

