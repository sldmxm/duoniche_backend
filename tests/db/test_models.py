import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.value_objects.answer import SentenceConstructionAnswer
from app.db.models import Exercise, ExerciseAnswer, ExerciseAttempt

pytestmark = pytest.mark.asyncio


async def test_exercise_model(async_session: AsyncSession):
    async with async_session as session:
        # Create
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

        assert exercise.exercise_id is not None

        # Read
        loaded = await session.get(Exercise, exercise.exercise_id)
        assert loaded is not None
        assert loaded.exercise_type == 'sentence_construction'

        # Delete
        await session.delete(exercise)
        await session.commit()

        result = await session.get(Exercise, exercise.exercise_id)
        assert result is None


async def test_relationships(async_session: AsyncSession):
    async with async_session as session:
        # Create exercise
        exercise = Exercise(
            exercise_type='sentence_construction',
            language_level='beginner',
            topic='test',
            exercise_text='test',
            data={},
        )
        session.add(exercise)
        await session.commit()

        # Refresh exercise after commit
        await session.refresh(exercise)

        # Create cached answer
        answer = SentenceConstructionAnswer(sentences=['Test sentence'])
        exercise_answer = ExerciseAnswer(
            exercise_id=exercise.exercise_id,
            answer=answer.model_dump(),
            answer_text=answer.get_answer_text(),
            is_correct=True,
            feedback='Good!',
        )
        session.add(exercise_answer)
        await session.commit()
        await session.refresh(exercise_answer)

        # Create attempt
        attempt = ExerciseAttempt(
            user_id=1,
            exercise_id=exercise.exercise_id,
            answer=answer.model_dump(),
            is_correct=True,
            feedback='Good!',
            exercise_answers_id=exercise_answer.answer_id,
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)

    # Test relationships (загрузка в другом контексте)
    async with async_session as session:
        loaded_exercise = await session.get(
            Exercise,
            exercise.exercise_id,
            options=[
                selectinload(Exercise.attempts),
                selectinload(Exercise.exercise_answers),
            ],
        )
        assert len(loaded_exercise.attempts) == 1
        assert len(loaded_exercise.exercise_answers) == 1
        assert loaded_exercise.attempts[0].attempt_id == attempt.attempt_id
        assert (
            loaded_exercise.exercise_answers[0].answer_id
            == exercise_answer.answer_id
        )

    # Test cascade delete
    async with async_session as session:
        await session.delete(exercise)
        await session.commit()

    # Verify cascade
    async with async_session as session:
        result = await session.execute(
            select(ExerciseAnswer).where(
                ExerciseAnswer.exercise_id == exercise.exercise_id
            )
        )
        assert result.scalar_one_or_none() is None

        result = await session.execute(
            select(ExerciseAttempt).where(
                ExerciseAttempt.exercise_id == exercise.exercise_id
            )
        )
        assert result.scalar_one_or_none() is None


async def test_cached_answer_created_at(async_session: AsyncSession):
    """Test that cached_answer have created_at field."""
    async with async_session as session:
        # Create exercise
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

        # Create cached answer
        answer = SentenceConstructionAnswer(sentences=['Test sentence'])
        cached_answer = ExerciseAnswer(
            exercise_id=exercise.exercise_id,
            answer=answer.model_dump(),
            answer_text=answer.get_answer_text(),
            is_correct=True,
            feedback='Good!',
        )
        session.add(cached_answer)
        await session.commit()
        await session.refresh(cached_answer)
        assert cached_answer.created_at is not None
