"""add tag fields

Revision ID: e4a5f6b7c8d9
Revises: 73120bbace3d
Create Date: 2025-06-17 10:00:00.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4a5f6b7c8d9'
down_revision: Union[str, None] = '73120bbace3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('exercises', sa.Column('grammar_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('exercise_answers', sa.Column('error_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('exercise_attempts', sa.Column('error_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('exercise_attempts', 'error_tags')
    op.drop_column('exercises', 'error_tags')
    op.drop_column('exercise_answers', 'error_tags')
