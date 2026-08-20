"""orders add proof_urls / proof_submitted_at

Revision ID: a1b2c3d4e5f7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-19 17:55:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("proof_urls", sa.String(length=2000), nullable=False, server_default=""))
    op.add_column("orders", sa.Column("proof_submitted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "proof_submitted_at")
    op.drop_column("orders", "proof_urls")
