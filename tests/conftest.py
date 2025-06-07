import os
import sys
from datetime import datetime
from typing import Any, AsyncGenerator, List
from unittest.mock import AsyncMock, create_autospec, patch

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.generation.config import ExerciseTopic
from app.core.interfaces.translate_provider import TranslateProvider
from app.core.services.async_task_cache import AsyncTaskCache
from app.core.services.exercise import ExerciseService
from app.core.services.payment import PaymentService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.services.user_settings import UserSettingsService
from app.db.models import DBUserBotProfile
from app.db.repositories.payment import SQLAlchemyPaymentRepository
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.llm.llm_translator import LLMTranslator
from app.services.choose_accent_generator import ChooseAccentGenerator
from app.services.file_storage_service import R2FileStorageService
from app.services.tts_service import GoogleTTSService

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
)

from app.api.dependencies import (
    get_exercise_service,
    get_user_bot_profile_service,
    get_user_progress_service,
    get_user_service,
    get_user_settings_service,
)
from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user import User
from app.core.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.value_objects.answer import (
    ChooseAccentAnswer,
    FillInTheBlankAnswer,
    StoryComprehensionAnswer,
)
from app.core.value_objects.exercise import (
    ChooseAccentExerciseData,
    FillInTheBlankExerciseData,
    StoryComprehensionExerciseData,
)
from app.db.base import Base
from app.db.models.exercise import Exercise as ExerciseModel
from app.db.models.exercise_answer import ExerciseAnswer as ExerciseAnswerModel
from app.db.models.user import User as UserModel
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.llm.llm_service import LLMService
from app.main import app


@pytest_asyncio.fixture(scope='session')
async def async_engine():
    """Create a SQLAlchemy async engine for the test session."""
    engine = create_async_engine(
        settings.test_database_url,
        echo=False,
        future=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope='function')
async def async_session(
    async_engine: AsyncEngine, redis: Redis
) -> AsyncGenerator[AsyncSession, Any]:
    """Create a SQLAlchemy async session for each test function."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async_session_factory = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await async_engine.dispose()
            await redis.flushdb()


@pytest_asyncio.fixture(scope='function')
async def db_session(
    async_session: AsyncSession,
) -> AsyncGenerator[AsyncSession, Any]:
    """DB session with nested transaction."""
    transaction = await async_session.begin_nested()
    try:
        yield async_session
    finally:
        if transaction.is_active:
            await transaction.rollback()
        await async_session.close()


@pytest_asyncio.fixture
async def redis() -> Redis:
    redis = Redis.from_url(settings.redis_url)
    await redis.select(settings.redis_test_db)
    await redis.flushdb()
    yield redis
    await redis.aclose()


@pytest_asyncio.fixture(scope='function')
async def exercise_service(db_session: AsyncSession, redis):
    """Create ExerciseService with test repositories"""
    return ExerciseService(
        exercise_repository=SQLAlchemyExerciseRepository(db_session),
        exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
            db_session
        ),
        exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
            db_session
        ),
        llm_service=LLMService(),
        translator=LLMTranslator(),
        async_task_cache=AsyncTaskCache(redis),
    )


@pytest_asyncio.fixture(scope='function')
async def user_service(db_session: AsyncSession):
    """Create ExerciseService with test repositories"""
    return UserService(SQLAlchemyUserRepository(db_session))


@pytest_asyncio.fixture(scope='function')
async def user_bot_profile_service(db_session: AsyncSession):
    """Create UserBotProfileService with test repositories"""
    return UserBotProfileService(
        profile_repo=SQLAlchemyUserBotProfileRepository(db_session)
    )


@pytest_asyncio.fixture(scope='function')
async def payment_service(db_session: AsyncSession):
    """Create UserBotProfileService with test repositories"""
    return PaymentService(
        payment_repository=SQLAlchemyPaymentRepository(db_session)
    )


@pytest_asyncio.fixture(scope='function')
async def user_settings_service(
    user_service: UserService,
    user_bot_profile_service: UserBotProfileService,
    redis: Redis,
):
    """Create UserBotProfileService with test repositories"""
    return UserSettingsService(
        user_service=user_service,
        user_bot_profile_service=user_bot_profile_service,
        redis_client=redis,
    )


@pytest_asyncio.fixture(scope='function')
async def user_progress_service(
    db_session,
    redis,
    user_service,
    exercise_service,
    user_bot_profile_service,
    payment_service,
    user_settings_service,
):
    """Create ExerciseService with test repositories"""
    return UserProgressService(
        user_service=user_service,
        exercise_service=exercise_service,
        user_bot_profile_service=user_bot_profile_service,
        payment_service=payment_service,
        user_settings_service=user_settings_service,
    )


@pytest_asyncio.fixture(scope='function')
async def client(
    user_progress_service,
    user_service,
    exercise_service,
    user_bot_profile_service,
) -> AsyncGenerator[AsyncClient, Any]:
    """Create test client with overridden dependencies"""

    def override_get_user_progress_service():
        return user_progress_service

    def override_get_user_service():
        return user_service

    def override_get_exercise_service():
        return exercise_service

    def override_get_user_bot_profile_service():
        return user_bot_profile_service

    def override_get_user_settings_service():
        return user_settings_service

    app.dependency_overrides[get_user_progress_service] = (
        override_get_user_progress_service
    )
    app.dependency_overrides[get_user_service] = override_get_user_service
    app.dependency_overrides[get_exercise_service] = (
        override_get_exercise_service
    )
    app.dependency_overrides[get_user_bot_profile_service] = (
        override_get_user_bot_profile_service
    )
    app.dependency_overrides[get_user_settings_service] = (
        override_get_user_settings_service
    )

    app.state.user_progress_service = user_progress_service
    app.state.exercise_service = exercise_service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        try:
            yield ac
        finally:
            del app.state.user_progress_service
            del app.state.exercise_service
            app.dependency_overrides.clear()


@pytest.fixture
def user_data():
    return {
        'user_id': 12345,
        'telegram_id': '67890',
        'username': 'testuser',
        'name': 'Test User',
    }


@pytest.fixture
def user(user_data):
    return User(**user_data)


@pytest_asyncio.fixture
async def add_db_user(
    db_session: AsyncSession,
    user,
):
    db_user_data = user.model_dump()
    db_user = UserModel(**db_user_data)

    db_session.add(db_user)
    await db_session.flush()
    yield db_user


@pytest.fixture
def user_bot_profile_data():
    return {
        'user_id': 12345,
        'bot_id': BotID.BG,
        'user_language': 'en',
        'language_level': LanguageLevel.A2,
    }


@pytest.fixture
def user_bot_profile(user_bot_profile_data):
    return UserBotProfile(**user_bot_profile_data)


@pytest_asyncio.fixture
async def add_user_bot_profile(
    db_session: AsyncSession,
    user_bot_profile,
):
    db_user_bot_profile = DBUserBotProfile(**user_bot_profile.model_dump())
    db_session.add(db_user_bot_profile)
    await db_session.flush()
    yield db_user_bot_profile


@pytest_asyncio.fixture
async def db_sample_exercise(db_session: AsyncSession, user):
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    exercise = ExerciseModel(
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language=BotID.BG.value,
        language_level=settings.default_language_level.value,
        topic=ExerciseTopic.GENERAL.value,
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data.model_dump(),
    )
    db_session.add(exercise)
    await db_session.flush()
    yield exercise


@pytest.fixture
def user_id_for_sample_request(user_data, db_sample_exercise):
    return user_data['user_id']


@pytest.fixture
def request_data_correct_answer_for_sample_exercise(
    user_data, db_sample_exercise
):
    return {
        'user_id': user_data['user_id'],
        'exercise_id': db_sample_exercise.exercise_id,
        'answer': {
            'exercise_type': 'fill_in_the_blank',
            'words': ['exercise'],
        },
    }


@pytest.fixture
def request_data_incorrect_answer_for_sample_exercise(
    user_data, db_sample_exercise
):
    return {
        'user_id': user_data['user_id'],
        'exercise_id': db_sample_exercise.exercise_id,
        'answer': {'exercise_type': 'fill_in_the_blank', 'words': ['wrong']},
    }


@pytest_asyncio.fixture
async def fill_sample_exercises(
    db_session: AsyncSession,
) -> AsyncGenerator[list[ExerciseModel], Any]:
    exercises = [
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.A1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='I ____ to the store yesterday.',
                words=['went'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.A2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='She has been ____ for three hours.',
                words=['studying'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.B1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='If I ____ more time, I would help you.',
                words=['had'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.B2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='The issue ____ in the latest meeting.',
                words=['was addressed'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language='en',
            language_level=LanguageLevel.C1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Fill in the blank in the sentence.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='The manuscript ____ to have '
                'been written in the 15th century.',
                words=['is believed'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language=BotID.BG.value,  # Bulgarian
            language_level=LanguageLevel.A1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Аз ____ до магазина вчера.',
                words=['отидох'],
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language=BotID.BG.value,  # Bulgarian
            language_level=LanguageLevel.A2.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Тя ____ от три часа.',
                words=['учи'],  # Пример
            ).model_dump(),
        ),
        ExerciseModel(
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language=BotID.BG.value,  # Bulgarian
            language_level=LanguageLevel.B1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Попълнете празното място в изречението.',
            data=FillInTheBlankExerciseData(
                text_with_blanks='Ако ____ повече време, щях да ти помогна.',
                words=['имах'],
            ).model_dump(),
        ),
    ]

    for exercise in exercises:
        db_session.add(exercise)
    await db_session.flush()
    yield exercises


@pytest.fixture
def get_exercises_by_level(fill_sample_exercises: List[ExerciseModel]) -> dict:
    """
    Returns a dictionary with exercises grouped by language level.
    """
    exercises_by_level = {}
    for exercise in fill_sample_exercises:
        if exercise.language_level not in exercises_by_level:
            exercises_by_level[exercise.language_level] = []
        exercises_by_level[exercise.language_level].append(exercise)

    return exercises_by_level


@pytest_asyncio.fixture
async def add_db_correct_exercise_answer(
    db_session: AsyncSession,
    db_sample_exercise,
    request_data_correct_answer_for_sample_exercise,
    user,
    user_bot_profile,
):
    """Create a correct ExerciseAnswerModel in the database."""
    exercise_answer = ExerciseAnswer(
        exercise_id=db_sample_exercise.exercise_id,
        answer=FillInTheBlankAnswer(
            words=request_data_correct_answer_for_sample_exercise['answer'][
                'words'
            ]
        ),
        is_correct=True,
        feedback='',
        feedback_language=user_bot_profile.user_language,
        created_by='LLM',
        created_at=datetime.now(),
        answer_id=1,
    )
    db_answer = ExerciseAnswerModel(
        exercise_id=exercise_answer.exercise_id,
        answer=exercise_answer.answer.model_dump(),
        answer_text=exercise_answer.answer.get_answer_text(),
        is_correct=exercise_answer.is_correct,
        feedback=exercise_answer.feedback,
        feedback_language=exercise_answer.feedback_language,
        created_at=exercise_answer.created_at,
        created_by=exercise_answer.created_by,
    )
    db_session.add(db_answer)
    await db_session.flush()
    yield db_answer


@pytest_asyncio.fixture
async def add_db_incorrect_exercise_answer(
    db_session: AsyncSession,
    db_sample_exercise,
    request_data_incorrect_answer_for_sample_exercise,
    user,
    user_bot_profile,
):
    """Create an incorrect ExerciseAnswerModel in the database."""
    exercise_answer = ExerciseAnswer(
        exercise_id=db_sample_exercise.exercise_id,
        answer=FillInTheBlankAnswer(
            words=request_data_incorrect_answer_for_sample_exercise['answer'][
                'words'
            ]
        ),
        is_correct=False,
        feedback='incorrect',
        feedback_language=user_bot_profile.user_language,
        created_by='LLM',
        created_at=datetime.now(),
        answer_id=1,
    )
    db_answer = ExerciseAnswerModel(
        exercise_id=exercise_answer.exercise_id,
        answer=exercise_answer.answer.model_dump(),
        answer_text=exercise_answer.answer.get_answer_text(),
        is_correct=exercise_answer.is_correct,
        feedback=exercise_answer.feedback,
        feedback_language=user_bot_profile.user_language,
        created_at=exercise_answer.created_at,
        created_by=exercise_answer.created_by,
    )
    db_session.add(db_answer)
    await db_session.flush()
    yield db_answer


@pytest.fixture
def fill_in_the_blank_exercise(user, user_bot_profile):
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='en',
        language_level=user_bot_profile.language_level,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data,
    )


@pytest_asyncio.fixture
async def mock_exercise_repository():
    """Mock ExerciseRepository for testing."""
    return create_autospec(SQLAlchemyExerciseRepository, instance=True)


@pytest_asyncio.fixture
async def mock_exercise_attempt_repository():
    """Mock ExerciseAttemptRepository for testing."""
    return create_autospec(SQLAlchemyExerciseAttemptRepository, instance=True)


@pytest_asyncio.fixture
async def mock_exercise_answer_repository():
    """Mock ExerciseAnswerRepository for testing."""
    return create_autospec(SQLAlchemyExerciseAnswerRepository, instance=True)


@pytest_asyncio.fixture
async def mock_llm_service():
    """Mock LLMService for testing."""
    return create_autospec(LLMService, instance=True)


@pytest.fixture
def mock_translator():
    mock = AsyncMock(spec=TranslateProvider)
    mock.translate_feedback.return_value = 'Translated feedback'
    return mock


@pytest.fixture
def fill_in_the_blank_answer():
    return FillInTheBlankAnswer(words=['exercise'])


@pytest.fixture(autouse=True)
def mock_get_next_exercise_level():
    """Mocks LanguageLevel.get_next_exercise_level for all tests."""
    with patch('app.core.enums.LanguageLevel.get_next_exercise_level') as mock:
        mock.return_value = LanguageLevel.A2
        yield mock


@pytest.fixture(autouse=True)
def mock_get_next_topic():
    """Mocks ExerciseTopic.get_next_topic for all tests."""
    with patch('app.core.generation.config.ExerciseTopic.get_topic') as mock:
        mock.return_value = ExerciseTopic.GENERAL
        yield mock


@pytest.fixture(autouse=True)
def mock_get_next_type():
    """Mocks ExerciseType.get_next_type for all tests."""
    with patch('app.core.enums.ExerciseType.get_next_type') as mock:
        mock.return_value = ExerciseType.FILL_IN_THE_BLANK
        yield mock


@pytest_asyncio.fixture
async def mock_tts_service():
    """Mock GoogleTTSService."""
    service = create_autospec(GoogleTTSService, instance=True)
    service.text_to_speech_ogg = AsyncMock(return_value=b'fake_ogg_data')
    return service


@pytest_asyncio.fixture
async def mock_file_storage_service():
    """Mock R2FileStorageService."""
    service = create_autospec(R2FileStorageService, instance=True)
    service.upload_audio = AsyncMock(
        return_value='http://fake-r2-url.com/audio.ogg'
    )
    return service


@pytest_asyncio.fixture
async def mock_http_client_telegram():
    """Mock httpx.AsyncClient for Telegram uploads."""
    client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'ok': True,
        'result': {
            'voice': {'file_id': 'fake_telegram_file_id'},
            'message_id': 12345,  # Добавим message_id для полноты
        },
    }
    client.post = AsyncMock(return_value=mock_response)
    return client


@pytest_asyncio.fixture
async def mock_llm_service_for_story(db_session: AsyncSession):
    """Specific LLMService mock for Story Comprehension generation."""
    service = create_autospec(LLMService, instance=True)

    async def async_generate_story_exercise_mock(*args, **kwargs):
        target_language = kwargs.get('target_language')
        language_level = kwargs.get('language_level')
        topic = kwargs.get('topic')
        exercise_type = kwargs.get('exercise_type')

        if exercise_type == ExerciseType.STORY_COMPREHENSION:
            story_data = StoryComprehensionExerciseData(
                content_text='This is a test story.',
                audio_url='',
                audio_telegram_file_id='',
                options=['Correct statement', 'Incorrect 1', 'Incorrect 2'],
            )
            exercise = Exercise(
                exercise_type=ExerciseType.STORY_COMPREHENSION,
                exercise_language=target_language,
                language_level=language_level,
                topic=topic,
                exercise_text=(
                    'Read the story and choose the correct statement.'
                ),
                status=ExerciseStatus.PUBLISHED,
                data=story_data,
            )
            answer_obj = StoryComprehensionAnswer(answer='Correct statement')
            return exercise, answer_obj
        else:
            return None, None

    service.generate_exercise = AsyncMock(
        side_effect=async_generate_story_exercise_mock
    )
    return service


@pytest_asyncio.fixture
async def mock_choose_accent_generator():
    """Mock ChooseAccentGenerator."""
    generator = create_autospec(ChooseAccentGenerator, instance=True)

    mock_exercise_data = ChooseAccentExerciseData(
        options=['строя̀вам', 'стро̀явам']
    )
    mock_exercise = Exercise(
        exercise_id=None,
        exercise_type=ExerciseType.CHOOSE_ACCENT,
        exercise_language='bg',
        language_level=LanguageLevel.A1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Изберете правилното ударение.',
        status=ExerciseStatus.PUBLISHED,
        data=mock_exercise_data,
    )
    mock_answer_obj = ChooseAccentAnswer(answer='стро̀явам')
    generator.generate = AsyncMock(
        return_value=(mock_exercise, mock_answer_obj)
    )
    return generator
