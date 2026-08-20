"""users username & parent switch

Revision ID: 7f3a9c21d4b8
Revises: 218608bbc4b0
Create Date: 2026-08-19 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f3a9c21d4b8'
down_revision: Union[str, None] = '218608bbc4b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('allow_parent_switch', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=True)
        batch_op.create_index('ix_users_username', ['username'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_username')
        batch_op.drop_column('username')
        batch_op.drop_column('allow_parent_switch')
        batch_op.alter_column('phone', existing_type=sa.String(length=20), nullable=False)
