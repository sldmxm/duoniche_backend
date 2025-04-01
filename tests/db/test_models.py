import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import SentenceConstructionAnswer
from app.db.models import Exercise, ExerciseAnswer, ExerciseAttempt

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sentence_construction_answer():
    return SentenceConstructionAnswer(sentences=['Test sentence'])


@pytest.fixture
def exercise_data():
    return {
        'exercise_type': ExerciseType.SENTENCE_CONSTRUCTION.value,
        'exercise_language': 'en',
        'language_level': LanguageLevel.B1.value,
        'topic': ExerciseTopic.GENERAL.value,
        'exercise_text': 'test',
        'data': {},
    }


@pytest_asyncio.fixture
async def exercise(async_session: AsyncSession, exercise_data):
    async with async_session as session:
        db_exercise = Exercise(**exercise_data)
        session.add(db_exercise)
        await session.commit()
        await session.refresh(db_exercise)
        yield db_exercise


@pytest_asyncio.fixture
async def exercise_answer(
    async_session: AsyncSession, exercise, sentence_construction_answer
):
    async with async_session as session:
        db_exercise_answer = ExerciseAnswer(
            exercise_id=exercise.exercise_id,
            answer=sentence_construction_answer.model_dump(),
            answer_text=sentence_construction_answer.get_answer_text(),
            is_correct=True,
            feedback='Good!',
        )
        session.add(db_exercise_answer)
        await session.commit()
        await session.refresh(db_exercise_answer)
        yield db_exercise_answer


@pytest_asyncio.fixture
async def exercise_attempt(
    async_session: AsyncSession,
    exercise,
    exercise_answer,
    sentence_construction_answer,
    add_db_user,
):
    async with async_session as session:
        db_exercise_attempt = ExerciseAttempt(
            user_id=add_db_user.user_id,
            exercise_id=exercise.exercise_id,
            answer=sentence_construction_answer.model_dump(),
            is_correct=True,
            feedback='Good!',
            answer_id=exercise_answer.answer_id,
        )
        session.add(db_exercise_attempt)
        await session.commit()
        await session.refresh(db_exercise_attempt)
        yield db_exercise_attempt


@pytest.mark.asyncio
async def test_exercise_model(async_session: AsyncSession, exercise):
    db_exercise = exercise
    async with async_session as session:
        assert db_exercise.exercise_id is not None

        # Read
        loaded = await session.get(Exercise, db_exercise.exercise_id)
        assert loaded is not None
        assert loaded.exercise_type == ExerciseType.SENTENCE_CONSTRUCTION.value

        # Delete
        await session.delete(db_exercise)
        await session.commit()

        result = await session.get(Exercise, db_exercise.exercise_id)
        assert result is None


@pytest.mark.asyncio
async def test_relationships(
    async_session: AsyncSession, exercise, exercise_answer, exercise_attempt
):
    db_exercise = exercise
    db_exercise_answer = exercise_answer
    db_exercise_attempt = exercise_attempt
    async with async_session as session:
        stmt = (
            select(Exercise)
            .where(Exercise.exercise_id == db_exercise.exercise_id)
            .options(
                selectinload(Exercise.attempts),
                selectinload(Exercise.exercise_answers),
            )
        )
        result = await session.execute(stmt)
        loaded_exercise = result.scalar_one()

        assert len(loaded_exercise.attempts) == 1
        assert len(loaded_exercise.exercise_answers) == 1
        assert (
            loaded_exercise.attempts[0].attempt_id
            == db_exercise_attempt.attempt_id
        )
        assert (
            loaded_exercise.exercise_answers[0].answer_id
            == db_exercise_answer.answer_id
        )

    # Test cascade delete
    async with async_session as session:
        await session.delete(db_exercise)
        await session.commit()

    # Verify cascade
    async with async_session as session:
        result = await session.execute(
            select(ExerciseAnswer).where(
                ExerciseAnswer.exercise_id == db_exercise.exercise_id
            )
        )
        assert result.scalar_one_or_none() is None

        result = await session.execute(
            select(ExerciseAttempt).where(
                ExerciseAttempt.exercise_id == db_exercise.exercise_id
            )
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cached_answer_created_at(
    async_session: AsyncSession, exercise, exercise_answer
):
    """Test that cached_answer have created_at field."""
    db_exercise_answer = exercise_answer
    assert db_exercise_answer.created_at is not None
