import os
import sys
from datetime import datetime
from typing import Any, AsyncGenerator, List
from unittest.mock import create_autospec

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

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_progress import UserProgressService
from app.db.repositories.user import SQLAlchemyUserRepository
from app.translator.translator import Translator

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
)

from app.api.dependencies import (
    get_exercise_service,
    get_user_progress_service,
    get_user_service,
)
from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
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
        translator=Translator(),
    )


@pytest_asyncio.fixture(scope='function')
async def user_service(db_session: AsyncSession):
    """Create ExerciseService with test repositories"""
    return UserService(SQLAlchemyUserRepository(db_session))


@pytest_asyncio.fixture(scope='function')
async def user_progress_service(db_session, redis):
    """Create ExerciseService with test repositories"""
    return UserProgressService(
        user_service=UserService(SQLAlchemyUserRepository(db_session)),
        exercise_service=ExerciseService(
            exercise_repository=SQLAlchemyExerciseRepository(db_session),
            exercise_attempt_repository=SQLAlchemyExerciseAttemptRepository(
                db_session
            ),
            exercise_answers_repository=SQLAlchemyExerciseAnswerRepository(
                db_session
            ),
            llm_service=LLMService(),
            translator=Translator(),
        ),
    )


@pytest_asyncio.fixture(scope='function')
async def client(
    user_progress_service,
    user_service,
    exercise_service,
) -> AsyncGenerator[AsyncClient, Any]:
    """Create test client with overridden dependencies"""

    def override_get_user_progress_service():
        return user_progress_service

    def override_get_user_service():
        return user_service

    def override_get_exercise_service():
        return exercise_service

    app.dependency_overrides[get_user_progress_service] = (
        override_get_user_progress_service
    )
    app.dependency_overrides[get_user_service] = override_get_user_service
    app.dependency_overrides[get_exercise_service] = (
        override_get_exercise_service
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
        'user_language': 'en',
        'target_language': 'en',
        'is_waiting_next_session': False,
        'exercises_get_in_session': 0,
        'exercises_get_in_set': 0,
        'errors_count_in_set': 0,
    }


@pytest.fixture
def user(user_data):
    user = User(**user_data)
    user.language_level = DEFAULT_LANGUAGE_LEVEL
    return User(**user_data)


@pytest_asyncio.fixture
async def add_db_user(
    db_session: AsyncSession,
    user,
):
    db_user_data = user.model_dump()
    db_user_data['language_level'] = user.language_level.value
    db_user = UserModel(**db_user_data)

    db_session.add(db_user)
    await db_session.flush()
    yield db_user


@pytest_asyncio.fixture
async def db_sample_exercise(db_session: AsyncSession, user):
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    exercise = ExerciseModel(
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level=DEFAULT_LANGUAGE_LEVEL.value,
        topic=ExerciseTopic.GENERAL.value,
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data.model_dump(),
    )
    db_session.add(exercise)
    await db_session.flush()
    yield exercise


@pytest.fixture
def sample_exercise_request_data(user_data, db_sample_exercise):
    return user_data['user_id']


@pytest.fixture
def request_data_correct_answer_for_sample_exercise(
    user_data, db_sample_exercise
):
    return {
        'user_id': user_data['user_id'],
        'exercise_id': db_sample_exercise.exercise_id,
        'answer': {'words': ['exercise']},
    }


@pytest.fixture
def request_data_incorrect_answer_for_sample_exercise(
    user_data, db_sample_exercise
):
    return {
        'user_id': user_data['user_id'],
        'exercise_id': db_sample_exercise.exercise_id,
        'answer': {'words': ['wrong']},
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
        feedback_language=user.user_language,
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
        feedback_language=user.user_language,
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
        feedback_language=user.user_language,
        created_at=exercise_answer.created_at,
        created_by=exercise_answer.created_by,
    )
    db_session.add(db_answer)
    await db_session.flush()
    yield db_answer


@pytest.fixture
def fill_in_the_blank_exercise(user):
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='en',
        language_level=user.language_level,
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


@pytest_asyncio.fixture
async def mock_translator():
    """Mock LLMService for testing."""
    return create_autospec(Translator, instance=True)


@pytest.fixture
def fill_in_the_blank_answer():
    return FillInTheBlankAnswer(words=['exercise'])
