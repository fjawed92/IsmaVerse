"""add profiles, favorites and reading streaks

Revision ID: e7a1c4d9b2f0
Revises: d1e2f3a4b5c6
Create Date: 2026-05-30 00:00:00.000000

Adds three brand-new tables (no ALTER on existing tables, so this is
SQLite-safe and needs no batch_alter_table):
  * user_profiles   — one avatar/display-name/theme per user
  * favorites        — favorited heroes/villains/comics
  * reading_streaks  — daily reading-streak tracker
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a1c4d9b2f0"
down_revision = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("avatar", sa.String(length=40), nullable=True),
        sa.Column("display_name", sa.String(length=80), nullable=True),
        sa.Column("theme", sa.String(length=20), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "item_type", "item_id", name="uq_favorite"),
    )
    op.create_table(
        "reading_streaks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("total_active_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
    )


def downgrade():
    op.drop_table("reading_streaks")
    op.drop_table("favorites")
    op.drop_table("user_profiles")
