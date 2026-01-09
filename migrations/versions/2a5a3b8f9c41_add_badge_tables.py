"""add badge tables

Revision ID: 2a5a3b8f9c41
Revises: 014452d35a3a
Create Date: 2026-01-09 02:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2a5a3b8f9c41"
down_revision = "014452d35a3a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.Column("progress_count", sa.Integer(), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )


def downgrade():
    op.drop_table("user_badges")
    op.drop_table("badges")
