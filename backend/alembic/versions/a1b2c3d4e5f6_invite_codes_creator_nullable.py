"""invite_codes.creator_id nullable for system codes

Revision ID: a1b2c3d4e5f6
Revises: f5a1b2c3d4e5
Create Date: 2026-08-19 17:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision = 'f5a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('invite_codes') as batch_op:
        batch_op.alter_column(
            'creator_id',
            existing_type=sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('invite_codes') as batch_op:
        batch_op.alter_column(
            'creator_id',
            existing_type=sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=False,
        )
