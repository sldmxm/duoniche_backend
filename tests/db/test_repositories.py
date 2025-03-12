from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.cached_answer import CachedAnswer as CachedAnswerEntity
from app.core.entities.exercise_attempt import (
    ExerciseAttempt as ExerciseAttemptEntity,
)
from app.core.value_objects.answer import SentenceConstructionAnswer
from app.db.models import Exercise
from app.db.repositories.cached_answer import SQLAlchemyCachedAnswerRepository
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def exercise(async_session: AsyncSession):
    exercise = None
    try:
        async with async_session as session:
            exercise = Exercise(
                exercise_type='sentence_construction',
                language_level='beginner',
                topic='test',
                exercise_text='test',
                data={},
            )
            session.add(exercise)
            await session.commit()
            await session.refresh(exercise)
            yield exercise
            await session.rollback()
    finally:
        if exercise:
            await session.delete(exercise)
            await session.commit()


async def test_cached_answer_repository(
    async_session: AsyncSession, exercise: Exercise
):
    async with async_session as session:
        repo = SQLAlchemyCachedAnswerRepository(session)
        answer = SentenceConstructionAnswer(sentences=['Test sentence'])

        # Test save
        cached_answer = await repo.save(
            CachedAnswerEntity(
                answer_id=0,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=True,
                feedback='Correct!',
                created_at=datetime.now(),
                created_by='test',
            )
        )
        assert cached_answer.answer_id is not None
        assert cached_answer.exercise_id == exercise.exercise_id

        # Test get by id
        loaded = await repo.get_by_id(cached_answer.answer_id)
        assert loaded is not None
        assert loaded.answer_id == cached_answer.answer_id
        assert loaded.answer.get_answer_text() == answer.get_answer_text()

        # Test get by exercise id
        answers = await repo.get_by_exercise_id(exercise.exercise_id)
        assert len(answers) == 1
        assert answers[0].answer_id == cached_answer.answer_id


async def test_exercise_attempt_repository(
    async_session: AsyncSession, exercise: Exercise
):
    async with async_session as session:
        repo = SQLAlchemyExerciseAttemptRepository(session)
        answer = SentenceConstructionAnswer(sentences=['Test sentence'])

        # Test save
        attempt = await repo.save(
            ExerciseAttemptEntity(
                attempt_id=0,
                user_id=1,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=True,
                feedback='Good job!',
                cached_answer_id=None,
            )
        )
        assert attempt.attempt_id is not None
        assert attempt.exercise_id == exercise.exercise_id

        # Test get by id
        loaded = await repo.get_by_id(attempt.attempt_id)
        assert loaded is not None
        assert loaded.attempt_id == attempt.attempt_id
        assert loaded.answer.get_answer_text() == answer.get_answer_text()

        # Test get by user and exercise
        attempts = await repo.get_by_user_and_exercise(1, exercise.exercise_id)
        assert len(attempts) == 1
        assert attempts[0].attempt_id == attempt.attempt_id

        # Test get all user attempts
        all_attempts = await repo.get_by_user_id(1)
        assert len(all_attempts) == 1
        assert all_attempts[0].attempt_id == attempt.attempt_id


async def test_exercise_attempt_repository_when_empty(
    async_session: AsyncSession,
):
    async with async_session as session:
        repo = SQLAlchemyExerciseAttemptRepository(session)
        async with session.begin():
            all_attempts = await repo.get_by_user_id(1)
            assert len(all_attempts) == 0

            attempts = await repo.get_by_user_and_exercise(1, 1)
            assert len(attempts) == 0
