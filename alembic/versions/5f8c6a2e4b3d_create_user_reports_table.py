"""create user_reports table

Revision ID: 5f8c6a2e4b3d
Revises: e4a5f6b7c8d9
Create Date: 2025-06-18 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f8c6a2e4b3d'
down_revision: Union[str, None] = 'e4a5f6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_reports',
    sa.Column('report_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('bot_id', sa.String(length=50), nullable=False),
    sa.Column('week_start_date', sa.Date(), nullable=False),
    sa.Column('short_report', sa.Text(), nullable=False),
    sa.Column('full_report', sa.Text(), nullable=False),
    sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index(op.f('ix_user_reports_bot_id'), 'user_reports', ['bot_id'], unique=False)
    op.create_index(op.f('ix_user_reports_report_id'), 'user_reports', ['report_id'], unique=False)
    op.create_index(op.f('ix_user_reports_user_id'), 'user_reports', ['user_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_reports_user_id'), table_name='user_reports')
    op.drop_index(op.f('ix_user_reports_report_id'), table_name='user_reports')
    op.drop_index(op.f('ix_user_reports_bot_id'), table_name='user_reports')
    op.drop_table('user_reports')
