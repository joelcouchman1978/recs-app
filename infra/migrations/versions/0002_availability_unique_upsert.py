"""availability unique constraint for upsert

Revision ID: 0002_availability_unique_upsert
Revises: 0001_init
Create Date: 2025-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = '0002_availability_unique_upsert'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a unique constraint to support ON CONFLICT upserts
    op.create_unique_constraint(
        'uq_availability_show_platform_offer',
        'availability',
        ['show_id', 'platform', 'offer_type'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_availability_show_platform_offer', 'availability', type_='unique')

