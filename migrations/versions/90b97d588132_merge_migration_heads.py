"""merge migration heads

Revision ID: 90b97d588132
Revises: 2a5a3b8f9c41, 6f6c2c2a0b5a
Create Date: 2026-01-09 03:54:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90b97d588132'
down_revision = ('2a5a3b8f9c41', '6f6c2c2a0b5a')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
