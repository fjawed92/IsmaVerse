"""add gender to characters

Revision ID: a3f7c2d1e8b9
Revises: c9d8e7f6a5b4
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f7c2d1e8b9'
down_revision = 'c9d8e7f6a5b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gender', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('characters', schema=None) as batch_op:
        batch_op.drop_column('gender')
