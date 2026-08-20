"""add usdt_address to withdrawal_orders

Revision ID: e4f0a1b2c3d4
Revises: c5d8e2f1a9b3
Create Date: 2026-08-19 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e4f0a1b2c3d4'
down_revision = 'c5d8e2f1a9b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('withdrawal_orders') as batch_op:
        batch_op.add_column(sa.Column('usdt_address', sa.String(length=100), nullable=False, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('withdrawal_orders') as batch_op:
        batch_op.drop_column('usdt_address')
