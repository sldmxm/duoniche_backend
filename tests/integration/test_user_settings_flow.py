import pytest
from httpx import AsyncClient

from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.enums import ExerciseType, LanguageLevel, UserAction, UserStatus
from app.core.generation.config import ExerciseTopic
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService

pytestmark = pytest.mark.asyncio


async def setup_user_and_profile(
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    user_id: int,
    telegram_id: str,
    user_status: UserStatus,
    bot_id: BotID = BotID.BG,
    language_level: LanguageLevel = LanguageLevel.A1,
    user_language: str = 'en',
    custom_settings_for_user: dict = None,
) -> tuple[User, UserBotProfile]:
    user_entity = User(
        user_id=user_id,
        telegram_id=telegram_id,
        username=f'testuser{user_id}',
        name=f'Test User {user_id}',
        status=user_status,
        telegram_data={'language_code': user_language},
        custom_settings=custom_settings_for_user,
    )
    db_user, _ = await user_service.get_or_create(user_entity)

    user_bot_profile, _ = await user_bot_profile_service.get_or_create(
        user_id=db_user.user_id,
        bot_id=bot_id,
        user_language=user_language,
        language_level=language_level,
    )
    await user_bot_profile_service.reset_and_start_new_session(
        user_id=db_user.user_id, bot_id=bot_id
    )
    # Re-fetch to ensure session data is fresh after reset
    user_bot_profile = await user_bot_profile_service.get(
        db_user.user_id, bot_id
    )
    return db_user, user_bot_profile


async def test_free_plan_session_limit_via_custom_settings(
    client: AsyncClient,
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    fill_sample_exercises,
):
    free_user_id = 101
    free_telegram_id = 'free_user_tg'
    bot_id = BotID.BG

    session_limit = 2
    custom_user_settings_values = {
        'session_exercise_limit': session_limit,
        'min_session_interval_minutes': 10,
        'exercises_in_set': session_limit + 1,  # Ensure set limit is higher
    }

    db_user, _ = await setup_user_and_profile(
        user_service,
        user_bot_profile_service,
        free_user_id,
        free_telegram_id,
        UserStatus.FREE,
        bot_id=bot_id,
        custom_settings_for_user=custom_user_settings_values,
    )

    for _ in range(custom_user_settings_values['session_exercise_limit']):
        response = await client.get(
            f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
        )
        assert response.status_code == 200
        action_data = response.json()
        assert action_data['action'] == UserAction.new_exercise.value
        assert action_data['exercise'] is not None

    response_after_limit = await client.get(
        f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
    )
    assert response_after_limit.status_code == 200
    action_data_after_limit = response_after_limit.json()
    assert (
        action_data_after_limit['action']
        == UserAction.congratulations_and_wait.value
    )
    assert 'pause' in action_data_after_limit


async def test_premium_plan_session_limit_via_custom_settings(
    client: AsyncClient,
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    fill_sample_exercises,
):
    premium_user_id = 102
    premium_telegram_id = 'premium_user_tg'
    bot_id = BotID.BG

    session_limit = 3
    custom_user_settings_values = {
        'session_exercise_limit': session_limit,
        'min_session_interval_minutes': 0,  # Premium might have 0 wait
        'exercises_in_set': session_limit + 1,  # Ensure set limit is higher
    }

    db_user, _ = await setup_user_and_profile(
        user_service,
        user_bot_profile_service,
        premium_user_id,
        premium_telegram_id,
        UserStatus.PREMIUM,
        bot_id=bot_id,
        custom_settings_for_user=custom_user_settings_values,
    )

    for _ in range(custom_user_settings_values['session_exercise_limit']):
        response = await client.get(
            f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
        )
        assert response.status_code == 200
        action_data = response.json()
        assert action_data['action'] == UserAction.new_exercise.value

    response_after_limit = await client.get(
        f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
    )
    assert response_after_limit.status_code == 200
    action_data_after_limit = response_after_limit.json()
    assert (
        action_data_after_limit['action']
        == UserAction.congratulations_and_wait.value
    )


async def test_user_settings_exclude_topics_via_custom_settings(
    client: AsyncClient,
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    fill_sample_exercises,
):
    user_id = 103
    telegram_id = 'exclude_topic_user_tg'
    bot_id = BotID.BG
    excluded_topic = ExerciseTopic.TRAVEL

    custom_user_settings_values = {
        'session_exercise_limit': 10,
        'min_session_interval_minutes': 10,
        'exercises_in_set': 2,
        'exclude_topics': [excluded_topic.value],  # MODIFIED HERE
    }

    db_user, _ = await setup_user_and_profile(
        user_service,
        user_bot_profile_service,
        user_id,
        telegram_id,
        UserStatus.FREE,
        bot_id=bot_id,
        custom_settings_for_user=custom_user_settings_values,
    )

    generated_topics = set()
    for _ in range(5):  # Request a few exercises
        response = await client.get(
            f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
        )
        assert response.status_code == 200
        action_data = response.json()
        if action_data['action'] == UserAction.new_exercise.value:
            assert action_data['exercise'] is not None
            generated_topics.add(
                ExerciseTopic(action_data['exercise']['topic'])
            )
        elif (
            action_data['action'] == UserAction.congratulations_and_wait.value
        ):  # Stop if session limit reached
            break
        # Handle praise_and_next_set if necessary,
        # or ensure enough exercises are generated before limit
        elif action_data['action'] == UserAction.praise_and_next_set.value:
            continue

    assert excluded_topic not in generated_topics
    assert len(generated_topics) > 0


async def test_user_settings_exercise_type_distribution_via_custom_settings(
    client: AsyncClient,
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    fill_sample_exercises,
):
    user_id = 104
    telegram_id = 'type_dist_user_tg'
    bot_id = BotID.BG

    # MODIFIED HERE: Use .value for enum keys
    specific_distribution_values = {ExerciseType.FILL_IN_THE_BLANK.value: 1.0}
    for ex_type in ExerciseType:
        if ex_type != ExerciseType.FILL_IN_THE_BLANK:
            specific_distribution_values[ex_type.value] = 0.0

    custom_user_settings_values = {
        'session_exercise_limit': 10,
        'min_session_interval_minutes': 10,
        'exercises_in_set': 2,
        'exercise_type_distribution': specific_distribution_values,
    }

    db_user, _ = await setup_user_and_profile(
        user_service,
        user_bot_profile_service,
        user_id,
        telegram_id,
        UserStatus.FREE,
        bot_id=bot_id,
        custom_settings_for_user=custom_user_settings_values,
    )

    generated_exercise_types = set()
    for _ in range(5):  # Request a few exercises
        response = await client.get(
            f'/api/v1/users/{db_user.user_id}/bots/{bot_id.value}/next-action/'
        )
        assert response.status_code == 200
        action_data = response.json()
        if action_data['action'] == UserAction.new_exercise.value:
            assert action_data['exercise'] is not None
            generated_exercise_types.add(
                ExerciseType(action_data['exercise']['exercise_type'])
            )
        elif (
            action_data['action'] == UserAction.congratulations_and_wait.value
        ):  # Stop if session limit reached
            break
        elif action_data['action'] == UserAction.praise_and_next_set.value:
            continue

    assert len(generated_exercise_types) > 0
    for ex_type in generated_exercise_types:
        assert ex_type == ExerciseType.FILL_IN_THE_BLANK
