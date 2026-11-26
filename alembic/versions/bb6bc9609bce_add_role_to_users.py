"""add role to users

Revision ID: bb6bc9609bce
Revises: e4cdc75b1de7
Create Date: 2026-11-26 16:13:34.642295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb6bc9609bce'
down_revision: Union[str, Sequence[str], None] = 'e4cdc75b1de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(length=20), server_default=sa.text("'customer'"), nullable=False))
    op.create_check_constraint('chk_users_role', 'users', "role IN ('customer', 'admin')")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('chk_users_role', 'users', type_='check')
    op.drop_column('users', 'role')
