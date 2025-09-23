"""initial schema

Revision ID: 0001_init
Revises: 
Create Date: 2025-09-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # profiles
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.Enum('Ross','Wife','Son', name='profilename'), nullable=False),
        sa.Column('age_limit', sa.Integer, nullable=True),
        sa.Column('boundaries', postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'])

    # shows
    op.create_table(
        'shows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('year_start', sa.Integer, nullable=True),
        sa.Column('year_end', sa.Integer, nullable=True),
        sa.Column('tmdb_id', sa.Integer, nullable=True),
        sa.Column('imdb_id', sa.String(32), nullable=True),
        sa.Column('jw_id', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('warnings', postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('flags', postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_shows_title', 'shows', ['title'])
    op.create_index('ix_shows_updated_at', 'shows', ['updated_at'])
    op.execute("CREATE INDEX IF NOT EXISTS ix_shows_metadata_gin ON shows USING GIN (metadata)")

    # availability
    offer_type = sa.Enum('stream','rent','buy', name='offer_type')
    offer_type.create(op.get_bind(), checkfirst=True)
    quality = sa.Enum('SD','HD','4K', name='quality')
    quality.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'availability',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('show_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform', sa.String(64), nullable=False),
        sa.Column('offer_type', offer_type, nullable=False),
        sa.Column('quality', quality, nullable=True),
        sa.Column('price_cents', sa.Integer, nullable=True),
        sa.Column('leaving_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_availability_show_id', 'availability', ['show_id'])

    # ratings
    op.create_table(
        'ratings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('profile_id', sa.Integer, sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('show_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('primary', sa.SmallInteger, nullable=False),
        sa.CheckConstraint('"primary" in (0,1,2)', name='ck_ratings_primary_enum'),
        sa.Column('nuance_tags', postgresql.ARRAY(sa.Text), server_default=sa.text("'{}'"), nullable=True),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_ratings_profile_id', 'ratings', ['profile_id'])
    op.create_index('ix_ratings_show_id', 'ratings', ['show_id'])

    # embeddings
    op.create_table(
        'embeddings_show',
        sa.Column('show_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shows.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('emb', sa.dialects.postgresql.ARRAY(sa.Float), nullable=False),  # store as float array in dev
    )

    op.create_table(
        'embeddings_profile',
        sa.Column('profile_id', sa.Integer, sa.ForeignKey('profiles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('emb', sa.dialects.postgresql.ARRAY(sa.Float), nullable=False),
    )

    # watchlist
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('profile_id', sa.Integer, sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('show_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('shows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # events
    op.create_table(
        'events',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('profile_id', sa.Integer, nullable=False),
        sa.Column('kind', sa.Text, nullable=False),
        sa.Column('payload', postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_events_payload_gin ON events USING GIN (payload)")


def downgrade() -> None:
    op.drop_index('ix_events_payload_gin')
    op.drop_table('events')
    op.drop_table('watchlist')
    op.drop_table('embeddings_profile')
    op.drop_table('embeddings_show')
    op.drop_index('ix_ratings_show_id', table_name='ratings')
    op.drop_index('ix_ratings_profile_id', table_name='ratings')
    op.drop_table('ratings')
    op.drop_index('ix_availability_show_id', table_name='availability')
    op.drop_table('availability')
    op.drop_index('ix_shows_updated_at', table_name='shows')
    op.drop_index('ix_shows_title', table_name='shows')
    op.drop_table('shows')
    op.drop_index('ix_profiles_user_id', table_name='profiles')
    op.drop_table('profiles')
    op.drop_table('users')

