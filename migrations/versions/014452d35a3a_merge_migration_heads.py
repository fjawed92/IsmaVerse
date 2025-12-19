"""merge migration heads

Revision ID: 014452d35a3a
Revises: 58d083bf9370, ba96b8a59eaf
Create Date: 2025-12-16 23:57:28.343463

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014452d35a3a'
down_revision = ('58d083bf9370', 'ba96b8a59eaf')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

