"""add arena battle and team battle tables

Revision ID: c9d8e7f6a5b4
Revises: b2c3d4e5f6a7
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'c9d8e7f6a5b4'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'arena_battle_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fighter1_type', sa.String(length=10), nullable=False),
        sa.Column('fighter1_id', sa.Integer(), nullable=False),
        sa.Column('fighter2_type', sa.String(length=10), nullable=False),
        sa.Column('fighter2_id', sa.Integer(), nullable=False),
        sa.Column('winner_type', sa.String(length=10), nullable=False),
        sa.Column('winner_id', sa.Integer(), nullable=False),
        sa.Column('narration', sa.Text(), nullable=True),
        sa.Column('session_key', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'team_battles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team1_name', sa.String(length=120), nullable=False),
        sa.Column('team1_members', sa.Text(), nullable=False),
        sa.Column('team2_name', sa.String(length=120), nullable=False),
        sa.Column('team2_members', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'team_battle_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_battle_id', sa.Integer(), sa.ForeignKey('team_battles.id'), nullable=False),
        sa.Column('winning_team', sa.Integer(), nullable=False),
        sa.Column('narration', sa.Text(), nullable=True),
        sa.Column('session_key', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('team_battle_votes')
    op.drop_table('team_battles')
    op.drop_table('arena_battle_votes')
