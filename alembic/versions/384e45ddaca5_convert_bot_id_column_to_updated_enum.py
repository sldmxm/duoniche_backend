"""convert_bot_id_column_to_updated_enum

Revision ID: 384e45ddaca5
Revises: 5c6a1d9eb64a
Create Date: 2025-06-03 19:02:45.256346

"""
from typing import Sequence, Union

from alembic import op

from app.core.entities.user_bot_profile import BotID

# revision identifiers, used by Alembic.
revision: str = '384e45ddaca5'
down_revision: Union[str, None] = '5c6a1d9eb64a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

enum_name = 'bot_id_enum'
table_name = 'user_bot_profiles'
column_name = 'bot_id'

def upgrade():
    op.execute(
        f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {enum_name} USING {column_name}::{enum_name};"
    )

def downgrade():
    for member in BotID:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = '{member.name}' WHERE {column_name} = '{member.value}';"
        )
