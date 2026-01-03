"""add hero customization fields

Revision ID: 6f6c2c2a0b5a
Revises: 5204eb624acb
Create Date: 2025-01-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6f6c2c2a0b5a"
down_revision = "5204eb624acb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_prompt", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("costume_color", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("boots_color", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("gloves_color", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("chest_symbol", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("eye_mask_color", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("cape_color", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("age", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hair_color", sa.String(length=80), nullable=True))


def downgrade():
    with op.batch_alter_table("characters", schema=None) as batch_op:
        batch_op.drop_column("hair_color")
        batch_op.drop_column("age")
        batch_op.drop_column("cape_color")
        batch_op.drop_column("eye_mask_color")
        batch_op.drop_column("chest_symbol")
        batch_op.drop_column("gloves_color")
        batch_op.drop_column("boots_color")
        batch_op.drop_column("costume_color")
        batch_op.drop_column("image_prompt")
