"""new fields for user progress

Revision ID: ac728e300f5e
Revises: 7e4e7bd50bdf
Create Date: 2025-04-05 13:28:49.567818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac728e300f5e'
down_revision: Union[str, None] = '7e4e7bd50bdf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('session_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('session_frozen_until', sa.DateTime(timezone=True), nullable=True))
    op.drop_column('users', 'is_waiting_next_session')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_waiting_next_session', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.drop_column('users', 'session_frozen_until')
    op.drop_column('users', 'session_started_at')
    # ### end Alembic commands ###
