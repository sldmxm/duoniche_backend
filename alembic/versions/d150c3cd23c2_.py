"""empty message

Revision ID: d150c3cd23c2
Revises: b60b2e4fe9b1
Create Date: 2025-03-19 22:58:17.451405

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'd150c3cd23c2'
down_revision: Union[str, None] = 'b60b2e4fe9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
