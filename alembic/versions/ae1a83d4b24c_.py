"""empty message

Revision ID: ae1a83d4b24c
Revises: 81ce30bb3bd4
Create Date: 2025-03-13 15:42:59.649117

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'ae1a83d4b24c'
down_revision: Union[str, None] = '81ce30bb3bd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
