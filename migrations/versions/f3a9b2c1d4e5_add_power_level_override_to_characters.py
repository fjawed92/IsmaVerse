"""add power_level_override to characters

Revision ID: f3a9b2c1d4e5
Revises: 014452d35a3a
Create Date: 2026-03-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a9b2c1d4e5'
down_revision = 'e1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.add_column(sa.Column('power_level_override', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.drop_column('power_level_override')
