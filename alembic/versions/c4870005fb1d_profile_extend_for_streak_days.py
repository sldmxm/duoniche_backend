"""profile extend for streak_days

Revision ID: c4870005fb1d
Revises: 381d12432191
Create Date: 2025-05-16 22:34:42.708774

"""
from datetime import date, datetime, timedelta, timezone
from typing import Sequence, Union, List

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from app.core.entities.user_bot_profile import BotID

# revision identifiers, used by Alembic.
revision: str = 'c4870005fb1d'
down_revision: Union[str, None] = '381d12432191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def calculate_streak_for_profile(
    activity_dates: List[date]
) -> int:
    """Calculate streak days for a user profile using synchronous logic."""
    if not activity_dates:
        return 0
    #  !!!Dates sorted in descending order while SQL query
    streak_count_historic = 0
    streak_ended_at_date = activity_dates[0]
    expected_previous_day_in_series = streak_ended_at_date

    for activity_day in activity_dates:
        if activity_day == expected_previous_day_in_series:
            streak_count_historic += 1
            expected_previous_day_in_series -= timedelta(days=1)
        elif activity_day < expected_previous_day_in_series:
            break

    current_streak_for_profile = 0
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    if streak_ended_at_date >= yesterday:
        current_streak_for_profile = streak_count_historic

    return current_streak_for_profile


def get_profile_activity_dates(connection, user_id: int, exercise_language: str) -> List[date]:
    """Get all activity dates for a user with a specific bot."""
    # Query to get all unique activity dates for a user's attempts on exercises of a specific bot
    query = text("""
        SELECT DISTINCT(DATE(ea.created_at)) as activity_date
        FROM exercise_attempts ea
        JOIN exercises e ON ea.exercise_id = e.exercise_id
        WHERE ea.user_id = :user_id
        AND e.exercise_language = :exercise_language
        ORDER BY activity_date DESC
    """)

    result = connection.execute(query, {"user_id": user_id, "exercise_language": exercise_language})
    activity_dates = [row[0] for row in result]
    return activity_dates


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add the column
    op.add_column(
        'user_bot_profiles',
        sa.Column('current_streak_days', sa.Integer(), nullable=False, server_default=sa.text('0'))
    )

    # 2. Set initial values to zero for existing rows that don't have values yet
    op.execute("UPDATE user_bot_profiles SET current_streak_days = 0 WHERE current_streak_days IS NULL")

    # 3. Get a synchronous connection
    connection = op.get_bind()

    # 4. Get all user profiles
    profiles_query = text("""
        SELECT user_id, bot_id
        FROM user_bot_profiles
    """)

    profiles_result = connection.execute(profiles_query)
    profiles_to_process = profiles_result.fetchall()

    print(f"Found {len(profiles_to_process)} profiles to process for streak calculation.")

    # 5. Process each profile
    profiles_with_streaks = 0
    processed_count = 0

    for row in profiles_to_process:
        profile_user_id = row[0]
        profile_bot_id = BotID[row[1]]
        try:
            # Get all activity dates for this user and bot
            activity_dates = get_profile_activity_dates(
                connection=connection,
                user_id=profile_user_id,
                exercise_language=profile_bot_id.value
            )

            # Calculate the streak
            streak = calculate_streak_for_profile(
                activity_dates
            )

            # Update the profile if streak > 0
            if streak > 0:
                profiles_with_streaks += 1
                update_query = text("""
                    UPDATE user_bot_profiles
                    SET current_streak_days = :streak
                    WHERE user_id = :user_id AND bot_id = :bot_id
                """)

                connection.execute(update_query, {
                    "streak": streak,
                    "user_id": profile_user_id,
                    "bot_id": profile_bot_id.name
                })

                print(f"  User ID: {profile_user_id}, Bot ID: {profile_bot_id} - Calculated streak: {streak}")

            if processed_count > 0 and processed_count % 100 == 0:
                print(f"Processed {processed_count} profiles...")

        except Exception as e:
            print(f"Error processing profile for user_id={profile_user_id}, bot_id={profile_bot_id}: {str(e)}")

        processed_count += 1

    print(f"Finished processing all {processed_count} profiles. Found {profiles_with_streaks} active streaks.")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_bot_profiles', 'current_streak_days')