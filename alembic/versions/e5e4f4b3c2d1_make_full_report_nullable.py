"""make full_report nullable

Revision ID: e5e4f4b3c2d1
Revises: f1bc5bd4324a
Create Date: 2025-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e4f4b3c2d1'
down_revision: Union[str, None] = 'f1bc5bd4324a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('user_reports', 'full_report',
               existing_type=sa.TEXT(),
               nullable=True)

def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('user_reports', 'full_report',
               existing_type=sa.TEXT(),
               nullable=False)
