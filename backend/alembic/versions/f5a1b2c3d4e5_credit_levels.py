"""credit_levels table + users.completed_order_count

Revision ID: f5a1b2c3d4e5
Revises: e4f0a1b2c3d4
Create Date: 2026-08-19 17:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f5a1b2c3d4e5'
down_revision = 'e4f0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'credit_levels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('min_orders', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('code'),
    )
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('completed_order_count', sa.Integer(), nullable=False, server_default='0'))
    op.execute(
        "UPDATE users SET completed_order_count = ("
        "SELECT COUNT(*) FROM orders o WHERE o.user_id = users.id AND o.status = 'COMPLETED')"
    )


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('completed_order_count')
    op.drop_table('credit_levels')
