"""add game scores and champions

Revision ID: f7b3c1a9d2e4
Revises: e7a1c4d9b2f0
Create Date: 2026-06-02 00:00:00.000000

Adds two brand-new tables (no ALTER on existing tables, so this is
SQLite-safe and needs no batch_alter_table):
  * game_scores     — per-game arcade scores for logged-in kids
  * game_champions  — one claimed hero + cosmetic XP/level per user
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f7b3c1a9d2e4"
down_revision = "e7a1c4d9b2f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "game_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_gamescore_game_score", "game_scores", ["game", "score"])
    op.create_table(
        "game_champions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.UniqueConstraint("user_id"),
    )


def downgrade():
    op.drop_table("game_champions")
    op.drop_index("ix_gamescore_game_score", table_name="game_scores")
    op.drop_table("game_scores")
