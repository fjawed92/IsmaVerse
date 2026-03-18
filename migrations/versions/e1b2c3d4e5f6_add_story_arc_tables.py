"""add story arc tables

Revision ID: e1b2c3d4e5f6
Revises: 2a5a3b8f9c41, 6f6c2c2a0b5a
Create Date: 2026-03-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'e1b2c3d4e5f6'
down_revision = ('2a5a3b8f9c41', '6f6c2c2a0b5a')
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    bind = op.get_bind()
    existing = inspect(bind).get_table_names()

    if 'story_arcs' in existing:
        return  # tables already created by another migration on this server

    op.create_table(
        'story_arcs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('tagline', sa.String(300), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.String(255), nullable=True),
        sa.Column('arc_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.String(30), nullable=False, server_default='ongoing'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'arc_heroes',
        sa.Column('arc_id', sa.Integer(), sa.ForeignKey('story_arcs.id'), primary_key=True),
        sa.Column('character_id', sa.Integer(), sa.ForeignKey('characters.id'), primary_key=True),
    )

    op.create_table(
        'arc_villains',
        sa.Column('arc_id', sa.Integer(), sa.ForeignKey('story_arcs.id'), primary_key=True),
        sa.Column('villain_id', sa.Integer(), sa.ForeignKey('villains.id'), primary_key=True),
    )

    op.create_table(
        'comic_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('arc_id', sa.Integer(), sa.ForeignKey('story_arcs.id'), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('cover_image', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'comic_panels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_id', sa.Integer(), sa.ForeignKey('comic_issues.id'), nullable=False),
        sa.Column('panel_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dialogue', sa.Text(), nullable=True),
        sa.Column('image_file', sa.String(255), nullable=True),
        sa.Column('image_prompt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('comic_panels')
    op.drop_table('comic_issues')
    op.drop_table('arc_villains')
    op.drop_table('arc_heroes')
    op.drop_table('story_arcs')
