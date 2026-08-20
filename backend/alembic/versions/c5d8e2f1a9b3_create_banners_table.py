"""create banners table

Revision ID: c5d8e2f1a9b3
Revises: 7f3a9c21d4b8
Create Date: 2026-08-19 11:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c5d8e2f1a9b3'
down_revision = '7f3a9c21d4b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('banners',
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('subtitle', sa.String(length=200), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=False),
    sa.Column('link_type', sa.String(length=20), nullable=False),
    sa.Column('link_value', sa.String(length=255), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('start_at', sa.DateTime(), nullable=True),
    sa.Column('end_at', sa.DateTime(), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_banners'))
    )
    op.create_index(op.f('ix_banners_status'), 'banners', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_banners_status'), table_name='banners')
    op.drop_table('banners')
