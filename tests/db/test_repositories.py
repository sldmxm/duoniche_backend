from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.exercise_answer import (
    ExerciseAnswer as ExerciseAnswerEntity,
)
from app.core.entities.exercise_attempt import (
    ExerciseAttempt as ExerciseAttemptEntity,
)
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.db.models import Exercise
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def exercise(async_session: AsyncSession):
    exercise = None
    try:
        async with async_session as session:
            exercise_data = FillInTheBlankExerciseData(
                text_with_blanks='This is a ____ test.', words=['great']
            )
            exercise = Exercise(
                exercise_type='fill_in_the_blank',
                exercise_language='en',
                language_level='beginner',
                topic='test',
                exercise_text='Fill in the blank',
                data=exercise_data.model_dump(),
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
        repo = SQLAlchemyExerciseAnswerRepository(session)
        answer = FillInTheBlankAnswer(words=['great'])

        # Test save
        exercise_answer = await repo.save(
            ExerciseAnswerEntity(
                answer_id=None,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=True,
                feedback='Correct!',
                created_at=datetime.now(),
                created_by='test',
            )
        )
        assert exercise_answer.answer_id is not None
        assert exercise_answer.exercise_id == exercise.exercise_id

        # Test get by id
        loaded = await repo.get_by_id(exercise_answer.answer_id)
        assert loaded is not None
        assert loaded.answer_id == exercise_answer.answer_id

        print(f'{loaded.answer.type=}')
        print(f'{answer.type=}')

        assert loaded.answer.get_answer_text() == answer.get_answer_text()
        assert loaded.answer.type == answer.type

        # Test get by exercise id
        loaded_by_exercise_id = await repo.get_by_exercise_id(
            exercise.exercise_id
        )
        assert loaded_by_exercise_id[0] is not None
        assert loaded_by_exercise_id[0].answer_id == exercise_answer.answer_id
        assert (
            loaded_by_exercise_id[0].answer.get_answer_text()
            == answer.get_answer_text()
        )
        assert loaded_by_exercise_id[0].answer.type == answer.type


async def test_exercise_attempt_repository(
    async_session: AsyncSession, exercise: Exercise
):
    async with async_session as session:
        repo = SQLAlchemyExerciseAttemptRepository(session)
        answer = FillInTheBlankAnswer(words=['great'])

        # Test save
        attempt = await repo.save(
            ExerciseAttemptEntity(
                attempt_id=0,
                user_id=1,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=True,
                feedback='Good job!',
                exercise_answer_id=None,
            )
        )
        assert attempt.attempt_id is not None
        assert attempt.exercise_id == exercise.exercise_id

        # Test get by id
        loaded = await repo.get_by_id(attempt.attempt_id)
        assert loaded is not None
        assert loaded.attempt_id == attempt.attempt_id
        assert loaded.answer.get_answer_text() == answer.get_answer_text()
        assert loaded.answer.type == answer.type

        # Test get by user and exercise
        attempts = await repo.get_by_user_and_exercise(1, exercise.exercise_id)
        assert len(attempts) == 1
        assert attempts[0].attempt_id == attempt.attempt_id
        assert attempts[0].answer.get_answer_text() == answer.get_answer_text()
        assert attempts[0].answer.type == answer.type

        # Test get all user attempts
        all_attempts = await repo.get_by_user_id(1)
        assert len(all_attempts) == 1
        assert all_attempts[0].attempt_id == attempt.attempt_id
        assert (
            all_attempts[0].answer.get_answer_text()
            == answer.get_answer_text()
        )
        assert all_attempts[0].answer.type == answer.type


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
