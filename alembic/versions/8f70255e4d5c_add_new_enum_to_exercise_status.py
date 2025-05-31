"""add_new_audio_related_statuses_to_exercise_status_enum

Revision ID: 8f70255e4d5c
Revises: ffa998e24036
Create Date: 2025-05-31 14:56:16.410072

"""
from typing import Sequence, Union

from alembic import op

from app.core.enums import ExerciseStatus

# revision identifiers, used by Alembic.
revision: str = '8f70255e4d5c'
down_revision: Union[str, None] = 'ffa998e24036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

enum_name = 'exercise_status_enum'
new_statuses = [
    ExerciseStatus.AUDIO_GENERATION_ERROR.value,
    ExerciseStatus.PROCESSING_ERROR_RETRY.value,
]

def upgrade() -> None:
    """Upgrade schema."""
    for status_value in new_statuses:
        op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{status_value}'")

def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL не поддерживает удаление значений из enum напрямую
    # Для полного отката потребуется пересоздание enum
    print(
        f"Downgrading migration {revision}: "
        f"Values {new_statuses} are not automatically removed from ENUM type {enum_name}. "
        f"To completely remove them, you would need to recreate the enum type."
    )