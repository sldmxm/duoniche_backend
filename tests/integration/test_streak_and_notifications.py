from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID
from app.core.enums import (
    ExerciseTopic,
    ExerciseType,
    UserAction,
)
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.texts import Reminder
from app.services.notification_producer import (
    NotificationProducerService,
)


@pytest.fixture
def mock_notification_producer() -> AsyncMock:
    return AsyncMock(spec=NotificationProducerService)


@pytest.fixture
def dummy_exercise(user: User) -> Exercise:
    """A dummy exercise to be returned by the mocked service."""
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language=BotID.BG.value,
        language_level=user.language_level,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Dummy exercise text',
        data={'text_with_blanks': 'dummy ____', 'words': ['text']},
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_streak_initial_exercise(
    user_progress_service: UserProgressService,
    user_bot_profile_service: UserBotProfileService,
    user_service: UserService,
    user: User,
    db_session,
    dummy_exercise: Exercise,
):
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    profile, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    assert profile.current_streak_days == 0
    assert profile.last_exercise_at is None

    with (
        freeze_time('2023-10-26 10:00:00 UTC'),
        patch.object(
            user_progress_service,
            '_get_next_exercise',
            return_value=dummy_exercise,
        ) as mock_get_exercise,
    ):
        next_action_result = await user_progress_service.get_next_action(
            user_id, bot_id
        )
        assert next_action_result.action == UserAction.new_exercise
        mock_get_exercise.assert_awaited_once()

    updated_profile = await user_bot_profile_service.get(user_id, bot_id)
    assert updated_profile is not None
    assert updated_profile.current_streak_days == 1
    assert updated_profile.last_exercise_at is not None
    assert (
        updated_profile.last_exercise_at.date()
        == datetime(2023, 10, 26, tzinfo=timezone.utc).date()
    )


@pytest.mark.asyncio
async def test_streak_next_day_exercise(
    user_progress_service: UserProgressService,
    user_bot_profile_service: UserBotProfileService,
    user_service: UserService,
    user: User,
    db_session,
    dummy_exercise: Exercise,
):
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    yesterday = datetime(2023, 10, 25, 15, 0, 0, tzinfo=timezone.utc)
    profile_data, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    profile_data.last_exercise_at = yesterday
    profile_data.current_streak_days = 1
    await user_bot_profile_service.save(profile_data)

    with (
        freeze_time('2023-10-26 10:00:00 UTC'),
        patch.object(
            user_progress_service,
            '_get_next_exercise',
            return_value=dummy_exercise,
        ) as mock_get_exercise,
    ):
        next_action_result = await user_progress_service.get_next_action(
            user_id, bot_id
        )
        assert next_action_result.action == UserAction.new_exercise
        mock_get_exercise.assert_awaited_once()

    updated_profile = await user_bot_profile_service.get(user_id, bot_id)
    assert updated_profile is not None
    assert updated_profile.current_streak_days == 2
    assert (
        updated_profile.last_exercise_at.date()
        == datetime(2023, 10, 26, tzinfo=timezone.utc).date()
    )


@pytest.mark.asyncio
async def test_streak_same_day_exercise(
    user_progress_service: UserProgressService,
    user_bot_profile_service: UserBotProfileService,
    user_service: UserService,
    user: User,
    db_session,
    dummy_exercise: Exercise,
):
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    today_morning = datetime(2023, 10, 26, 9, 0, 0, tzinfo=timezone.utc)
    profile_data, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    profile_data.last_exercise_at = today_morning
    profile_data.current_streak_days = 1
    await user_bot_profile_service.save(profile_data)

    with (
        freeze_time('2023-10-26 10:00:00 UTC'),
        patch.object(
            user_progress_service,
            '_get_next_exercise',
            return_value=dummy_exercise,
        ) as mock_get_exercise,
    ):
        next_action_result = await user_progress_service.get_next_action(
            user_id, bot_id
        )
        assert next_action_result.action == UserAction.new_exercise
        mock_get_exercise.assert_awaited_once()

    updated_profile = await user_bot_profile_service.get(user_id, bot_id)
    assert updated_profile is not None
    assert updated_profile.current_streak_days == 1
    assert (
        updated_profile.last_exercise_at.date()
        == datetime(2023, 10, 26, tzinfo=timezone.utc).date()
    )
    assert (
        updated_profile.last_exercise_at.time()
        == datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc).time()
    )


@pytest.mark.asyncio
async def test_streak_exercise_after_one_day_gap(
    user_progress_service: UserProgressService,
    user_bot_profile_service: UserBotProfileService,
    user_service: UserService,
    user: User,
    db_session,
    dummy_exercise: Exercise,
):
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    day_before_yesterday = datetime(
        2023, 10, 24, 15, 0, 0, tzinfo=timezone.utc
    )
    profile_data, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    profile_data.last_exercise_at = day_before_yesterday
    profile_data.current_streak_days = 5
    await user_bot_profile_service.save(profile_data)

    with (
        freeze_time('2023-10-26 10:00:00 UTC'),
        patch.object(
            user_progress_service,
            '_get_next_exercise',
            return_value=dummy_exercise,
        ) as mock_get_exercise,
    ):
        next_action_result = await user_progress_service.get_next_action(
            user_id, bot_id
        )
        assert next_action_result.action == UserAction.new_exercise
        mock_get_exercise.assert_awaited_once()

    updated_profile = await user_bot_profile_service.get(user_id, bot_id)
    assert updated_profile is not None
    assert updated_profile.current_streak_days == 1
    assert (
        updated_profile.last_exercise_at.date()
        == datetime(2023, 10, 26, tzinfo=timezone.utc).date()
    )


@pytest.mark.asyncio
@freeze_time('2023-10-26 10:00:00 UTC')
async def test_long_break_1d_reminder_no_streak(
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    user: User,
):
    # Ensure user_language is set for the test
    user.user_language = 'ru'
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    profile, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    profile.current_streak_days = 1
    await user_bot_profile_service.save(profile)

    producer_instance = NotificationProducerService()

    with patch.object(
        producer_instance, 'enqueue_notification', new_callable=AsyncMock
    ) as mock_enqueue:
        mock_enqueue.return_value = True

        await producer_instance.prepare_and_enqueue_long_break_reminder(
            user=created_user,
            user_profile=profile,
            reminder_type='1d',
            days_inactive=1,
        )

        mock_enqueue.assert_awaited_once()

        with patch(
            'app.services.notification_producer.get_text'
        ) as mock_get_text:
            mock_get_text.return_value = 'Mocked Text'
            producer_instance._get_long_break_reminder_text(
                user_profile=profile, reminder_type='1d'
            )
            mock_get_text.assert_called_once_with(
                key=Reminder.LONG_BREAK_1D,
                language_code=profile.user_language,
            )
            call_kwargs = mock_get_text.call_args.kwargs
            assert 'streak_days' not in call_kwargs


@pytest.mark.asyncio
@freeze_time('2023-10-26 10:00:00 UTC')
async def test_long_break_1d_reminder_with_streak(
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    user: User,
):
    user.user_language = 'ru'
    created_user, _ = await user_service.get_or_create(user)
    user_id = created_user.user_id
    bot_id = BotID.BG

    profile, _ = await user_bot_profile_service.get_or_create(
        user_id=user_id,
        bot_id=bot_id,
        user_language=created_user.user_language,
        language_level=created_user.language_level,
    )
    profile.current_streak_days = 5
    await user_bot_profile_service.save(profile)

    producer_instance = NotificationProducerService()
    with patch.object(
        producer_instance, 'enqueue_notification', new_callable=AsyncMock
    ) as mock_enqueue:
        mock_enqueue.return_value = True

        await producer_instance.prepare_and_enqueue_long_break_reminder(
            user=created_user,
            user_profile=profile,
            reminder_type='1d',
            days_inactive=1,
        )

        mock_enqueue.assert_awaited_once()

        with patch(
            'app.services.notification_producer.get_text'
        ) as mock_get_text:
            mock_get_text.return_value = 'Mocked Streak Text'
            producer_instance._get_long_break_reminder_text(
                user_profile=profile, reminder_type='1d'
            )
            mock_get_text.assert_called_once_with(
                key=Reminder.LONG_BREAK_1D_STREAK,
                language_code=profile.user_language,
                streak_days=5,
            )
