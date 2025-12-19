"""add roles column to users

Revision ID: 1a5a4f5e4d1a
Revises: 014452d35a3a
Create Date: 2025-12-17 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a5a4f5e4d1a'
down_revision = '014452d35a3a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('roles', sa.String(length=120), nullable=False, server_default='user')
    )
    op.alter_column('users', 'roles', server_default=None)


def downgrade():
    op.drop_column('users', 'roles')
