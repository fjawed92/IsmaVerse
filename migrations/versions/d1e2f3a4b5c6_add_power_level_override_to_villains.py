"""add power_level_override to villains

Revision ID: d1e2f3a4b5c6
Revises: c9d8e7f6a5b4
Create Date: 2026-03-29

"""
from alembic import op
import sqlalchemy as sa

revision = 'd1e2f3a4b5c6'
down_revision = 'a3f7c2d1e8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('villains', sa.Column('power_level_override', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('villains', 'power_level_override')
