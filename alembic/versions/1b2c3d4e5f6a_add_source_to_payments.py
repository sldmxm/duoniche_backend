"""add_source_to_payments

Revision ID: 1b2c3d4e5f6a
Revises: 9e3ca364e1ee
Create Date: 2025-07-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b2c3d4e5f6a'
down_revision: Union[str, None] = '9e3ca364e1ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('source', sa.String(length=50), server_default='session_unlock', nullable=False))

def downgrade() -> None:
    op.drop_column('payments', 'source')
