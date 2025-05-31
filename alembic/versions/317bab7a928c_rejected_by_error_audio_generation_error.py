"""rejected_by_error -> audio_generation_error

Revision ID: 317bab7a928c
Revises: 8f70255e4d5c
Create Date: 2025-05-31 18:12:12.084941

"""
from typing import Sequence, Union

from alembic import op

from app.core.enums import ExerciseStatus

# revision identifiers, used by Alembic.
revision: str = '317bab7a928c'
down_revision: Union[str, None] = '8f70255e4d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


tables_with_enum = [
    ('exercises', 'status'),
]

def upgrade() -> None:
    """Upgrade schema."""
    for table_name, column_name in tables_with_enum:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = '{ExerciseStatus.AUDIO_GENERATION_ERROR.value}' "
            f"WHERE {column_name} = 'rejected_by_error'"
        )

def downgrade() -> None:
    """Downgrade schema."""
    for table_name, column_name in tables_with_enum:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = 'rejected_by_error' "
            f"WHERE {column_name} = '{ExerciseStatus.AUDIO_GENERATION_ERROR.value}'"
        )
