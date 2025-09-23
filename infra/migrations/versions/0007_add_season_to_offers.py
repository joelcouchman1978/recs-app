from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_add_season_to_offers'
down_revision = '0006_offers_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('justwatch_offers', sa.Column('season', sa.Integer(), nullable=True))
    op.create_index('ix_offers_season', 'justwatch_offers', ['season'])


def downgrade() -> None:
    op.drop_index('ix_offers_season', table_name='justwatch_offers')
    op.drop_column('justwatch_offers', 'season')

