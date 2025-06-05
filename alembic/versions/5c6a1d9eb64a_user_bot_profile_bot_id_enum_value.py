"""Prepare data and add new enum values for bot_id

Revision ID: 5c6a1d9eb64a
Revises: ff5d5d529cd2
Create Date: 2025-06-03 18:37:21.170847

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

from app.core.entities.user_bot_profile import BotID

# revision identifiers, used by Alembic.
revision: str = '5c6a1d9eb64a'
down_revision: Union[str, None] = 'ff5d5d529cd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


enum_name = 'bot_id_enum'
table_name = 'user_bot_profiles'
column_name = 'bot_id'


def upgrade():
    op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE TEXT USING {column_name}::text;")

    for member in BotID:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = '{member.value}' WHERE {column_name} = '{member.name}';"
        )

    conn = op.get_bind()
    res = conn.execute(text(f"SELECT unnest(enum_range(NULL::{enum_name}))::text")).fetchall()
    existing_enum_values = {row[0] for row in res}

    new_enum_member_values = [member.value for member in BotID]

    for new_val in new_enum_member_values:
        if new_val not in existing_enum_values:
            conn.execute(text("COMMIT"))
            conn.execute(text(f"ALTER TYPE {enum_name} ADD VALUE '{new_val}';"))
            conn.execute(text("BEGIN"))


def downgrade():
    for member in BotID:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = '{member.name}' WHERE {column_name} = '{member.value}';"
        )
    op.execute(f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {enum_name} USING {column_name}::{enum_name};")

    for member in BotID:
        op.execute(
            f"UPDATE {table_name} SET {column_name} = '{member.name}' WHERE {column_name} = '{member.value}';"
        )