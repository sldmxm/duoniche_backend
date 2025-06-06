"""new fields for user

Revision ID: 6b35378d065b
Revises: ac728e300f5e
Create Date: 2025-04-07 19:40:06.069372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b35378d065b'
down_revision: Union[str, None] = 'ac728e300f5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('cohort', sa.String(), nullable=True))
    op.add_column('users', sa.Column('plan', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'plan')
    op.drop_column('users', 'cohort')
    # ### end Alembic commands ###
