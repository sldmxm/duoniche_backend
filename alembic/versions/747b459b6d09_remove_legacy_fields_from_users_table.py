"""remove_legacy_fields_from_users_table

Revision ID: 747b459b6d09
Revises: ac0b66d571dd
Create Date: 2025-05-28 16:16:41.755376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '747b459b6d09'
down_revision: Union[str, None] = 'ac0b66d571dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'user_language')
    op.drop_column('users', 'last_exercise_at')
    op.drop_column('users', 'language_level')
    op.drop_column('users', 'errors_count_in_set')
    op.drop_column('users', 'target_language')
    op.drop_column('users', 'exercises_get_in_session')
    op.drop_column('users', 'exercises_get_in_set')
    op.drop_column('users', 'session_started_at')
    op.drop_column('users', 'session_frozen_until')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('session_frozen_until', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('session_started_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('exercises_get_in_set', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('exercises_get_in_session', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('target_language', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('errors_count_in_set', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('language_level', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('last_exercise_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('user_language', sa.VARCHAR(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
