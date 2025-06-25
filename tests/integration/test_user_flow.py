from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.dependencies import get_language_config_service
from app.config import settings
from app.core.entities.user import User
from app.core.enums import LanguageLevel, UserAction
from app.core.services.payment import (
    INITIATE_PAYMENT_PREFIX,
    SESSION_UNLOCK_PREFIX,
)
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text
from app.db.models.exercise import Exercise as ExerciseModel
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.main import app

# Используем pytestmark для применения ко всем тестам в модуле
pytestmark = pytest.mark.asyncio


async def test_flow_session_limit_reached_offers_payment(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
):
    # Arrange: Create user and profile in a separate, committed transaction
    now = datetime.now(timezone.utc)
    user_id = user_data['user_id']
    bot_id = 'Bulgarian'
    user_language = 'ru'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        user_bot_profile, _ = await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )

        await setup_profile_service.update_session(
            user_id=db_user.user_id,
            bot_id=bot_id,
            exercises_get_in_session=(
                settings.exercises_in_set * settings.sets_in_session
            ),
            session_started_at=now - timedelta(minutes=1),
            session_frozen_until=None,
        )
        await setup_session.commit()

    # Act
    with freeze_time(now):
        next_action = await user_progress_service.get_next_action(
            user_id=db_user.user_id, bot_id=bot_id
        )

    # Assert
    assert next_action.action == UserAction.congratulations_and_wait

    assert next_action.keyboard is not None
    assert next_action.keyboard[0]['text'] == get_text(
        PaymentMessages.BUTTON_TEXT, user_bot_profile.user_language
    )
    assert next_action.keyboard[0]['callback_data'] == (
        f'{INITIATE_PAYMENT_PREFIX}:{SESSION_UNLOCK_PREFIX}'
    )

    expected_message_key = Messages.CONGRATULATIONS_AND_WAIT
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        exercise_num=settings.exercises_in_set * settings.sets_in_session,
        pause_time=str(settings.delta_between_sessions).split('.')[0],
    )
    assert next_action.message == expected_message
    assert next_action.pause == settings.delta_between_sessions


async def test_flow_frozen_user_offers_payment(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
):
    # Arrange
    now = datetime.now(timezone.utc)
    frozen_until = now + timedelta(hours=1)
    user_id = user_data['user_id']
    bot_id = 'Bulgarian'
    user_language = 'en'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        user_bot_profile, _ = await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )

        await setup_session.flush()

        await setup_profile_service.update_session(
            user_id=db_user.user_id,
            bot_id=bot_id,
            session_frozen_until=frozen_until,
        )
        await setup_session.commit()

    # Act
    with freeze_time(now):
        next_action = await user_progress_service.get_next_action(
            user_id=db_user.user_id, bot_id=bot_id
        )

    # Assert
    assert next_action.action == UserAction.limit_reached

    assert next_action.keyboard is not None
    assert next_action.keyboard[0]['text'] == get_text(
        PaymentMessages.BUTTON_TEXT, user_bot_profile.user_language
    )
    assert next_action.keyboard[0]['callback_data'] == (
        f'{INITIATE_PAYMENT_PREFIX}:{SESSION_UNLOCK_PREFIX}'
    )

    expected_message_key = Messages.LIMIT_REACHED
    delta_to_next_session = str(frozen_until - now).split('.')[0]
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        pause_time=delta_to_next_session,
    )
    assert next_action.message == expected_message


async def test_flow_new_exercise_for_active_user(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
    fill_sample_exercises,
    user_bot_profile_service,
):
    # Arrange
    user_id = user_data['user_id']
    bot_id = 'Bulgarian'
    user_language = 'bg'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )
        await setup_profile_service.reset_and_start_new_session(
            user_id=db_user.user_id, bot_id=bot_id
        )
        await setup_session.commit()

    # Act
    next_action = await user_progress_service.get_next_action(
        user_id=user_id, bot_id=bot_id
    )

    # Assert
    assert next_action.action == UserAction.new_exercise
    assert next_action.exercise is not None
    assert next_action.message is None
    assert next_action.keyboard is None

    updated_profile = await user_bot_profile_service.get(
        db_user.user_id, bot_id
    )
    assert updated_profile is not None
    assert updated_profile.exercises_get_in_session == 1
    assert updated_profile.exercises_get_in_set == 1
    assert updated_profile.last_exercise_at is not None


async def test_full_user_flow_for_new_language(
    client,
    mock_language_config_service_factory,
    async_session_maker,
):
    """
    Tests the end-to-end flow for a new language (Serbian).
    1. Mocks LanguageConfigService to include Serbian.
    2. Creates a Serbian exercise in the database.
    3. Simulates user registration for the Serbian bot.
    4. Requests a next action and verifies the returned exercise is Serbian.
    """
    # 1. Setup mock config with Serbian
    serbian_bot_id = 'Serbian'
    test_config = {
        'Bulgarian': {},  # Keep Bulgarian to avoid breaking other parts
        serbian_bot_id: {
            'bot_id': serbian_bot_id,
            'language_code': 'sr',
            'exercise_type_distribution': {'fill_in_the_blank': 1.0},
            'topics_exclude_from_generation': [],
        },
    }

    # 2. Add a dummy serbian exercise to DB
    from app.core.enums import ExerciseType, LanguageLevel
    from app.core.generation.config import ExerciseTopic

    async with async_session_maker() as session:
        exercise = ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language=serbian_bot_id,
            language_level=LanguageLevel.A2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Popuni prazno mesto.',
            data={
                'type': 'FillInTheBlankExerciseData',
                'text_with_blanks': 'Ja ___ u prodavnicu.',
                'words': ['idem'],
            },
        )
        session.add(exercise)
        await session.commit()

    # Override dependency for this test
    mock_service = mock_language_config_service_factory(test_config)
    app.dependency_overrides[get_language_config_service] = (
        lambda: mock_service
    )

    # 3. Simulate user registration for Serbian bot
    user_data = {
        'telegram_id': 'serbian_user_1',
        'username': 'serbian_user',
        'name': 'Serbian User',
        'user_language': 'en',
        'target_language': serbian_bot_id,
    }
    response = await client.put('/api/v1/users/', json=user_data)
    assert response.status_code == 200, response.text
    user_id = response.json()['user_id']

    # 4. Request next action and verify exercise
    response = await client.get(
        f'/api/v1/users/{user_id}/bots/{serbian_bot_id}/next-action/'
    )
    assert response.status_code == 200, response.text
    action_data = response.json()
    assert action_data['action'] == 'new_exercise'
    assert action_data['exercise']['exercise_language'] == serbian_bot_id
    # Cleanup dependency override
    app.dependency_overrides.pop(get_language_config_service, None)
