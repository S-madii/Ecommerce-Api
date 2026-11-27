"""change default currency from DZD to USD

Revision ID: a1f3c7d92e10
Revises: bb6bc9609bce
Create Date: 2026-11-27 09:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1f3c7d92e10'
down_revision: Union[str, Sequence[str], None] = 'bb6bc9609bce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Only the column defaults change; existing rows keep their stored currency."""
    op.alter_column('orders', 'currency', existing_type=sa.CHAR(length=3),
                    server_default=sa.text("'USD'"), existing_nullable=False)
    op.alter_column('payments', 'currency', existing_type=sa.CHAR(length=3),
                    server_default=sa.text("'USD'"), existing_nullable=False)


def downgrade() -> None:
    op.alter_column('payments', 'currency', existing_type=sa.CHAR(length=3),
                    server_default=sa.text("'DZD'"), existing_nullable=False)
    op.alter_column('orders', 'currency', existing_type=sa.CHAR(length=3),
                    server_default=sa.text("'DZD'"), existing_nullable=False)
