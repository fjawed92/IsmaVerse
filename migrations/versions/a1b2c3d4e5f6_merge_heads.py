"""merge heads

Revision ID: a1b2c3d4e5f6
Revises: f14b514bdbb2, f3a9b2c1d4e5
Create Date: 2026-03-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = ('f14b514bdbb2', 'f3a9b2c1d4e5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
