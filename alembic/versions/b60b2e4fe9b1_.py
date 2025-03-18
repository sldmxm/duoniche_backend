"""empty message

Revision ID: b60b2e4fe9b1
Revises: 6951b13fb891
Create Date: 2025-03-18 13:31:44.318559

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'b60b2e4fe9b1'
down_revision: Union[str, None] = '6951b13fb891'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
