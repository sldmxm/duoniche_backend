import pytest

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_cached_answer_repository(
    db_session,
    add_db_correct_exercise_answer,
):
    """Test cached answer repository."""
    assert add_db_correct_exercise_answer.answer_id == 1


@pytest.mark.asyncio
async def test_exercise_attempt_repository(
    db_session,
    add_db_correct_exercise_answer,
):
    """Test exercise attempt repository."""
    assert add_db_correct_exercise_answer.answer_id == 1


@pytest.mark.asyncio
async def test_get_by_id(db_session, db_sample_exercise):
    """Test getting an exercise by ID."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise = await repository.get_by_id(db_sample_exercise.exercise_id)

    assert exercise.exercise_id == db_sample_exercise.exercise_id
    assert exercise.exercise_type.value == db_sample_exercise.exercise_type
    assert exercise.exercise_language == db_sample_exercise.exercise_language
    assert exercise.language_level.value == db_sample_exercise.language_level
    assert exercise.topic.value == db_sample_exercise.topic
    assert exercise.exercise_text == db_sample_exercise.exercise_text
    assert (
        exercise.data.text_with_blanks
        == db_sample_exercise.data['text_with_blanks']
    )
    assert exercise.data.words == db_sample_exercise.data['words']


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session):
    """Test getting an exercise by ID when it doesn't exist."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise = await repository.get_by_id(99999)
    assert exercise is None


@pytest.mark.asyncio
async def test_get_all(db_session, fill_sample_exercises):
    """Test getting all exercises."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercises = await repository.get_all()
    assert len(exercises) == len(fill_sample_exercises)
    for exercise in exercises:
        assert isinstance(exercise, Exercise)


@pytest.mark.asyncio
async def test_get_new_exercise(
    db_session, get_exercises_by_level, user, add_db_user
):
    """Test getting exercises by language level and topic."""
    exercise_repository = SQLAlchemyExerciseRepository(db_session)
    language_level = LanguageLevel.B1
    topic = ExerciseTopic.GENERAL
    exercise = await exercise_repository.get_new_exercise(
        language_level=language_level,
        topic=topic,
        user=user,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
    )
    assert exercise.language_level == language_level
    assert exercise.topic == topic

    attempt_repository = SQLAlchemyExerciseAttemptRepository(db_session)
    await attempt_repository.create(
        ExerciseAttempt(
            user_id=user.user_id,
            exercise_id=exercise.exercise_id,
            answer=FillInTheBlankAnswer(
                words=[
                    'test',
                ]
            ),
            is_correct=True,
            feedback='Test feedback',
            answer_id=None,
            attempt_id=None,
        )
    )

    exercise = await exercise_repository.get_new_exercise(
        language_level=language_level,
        topic=topic,
        user=user,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
    )
    assert exercise is None


@pytest.mark.asyncio
async def test_save(db_session):
    """Test saving a new exercise."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='I ____ to the store.', words=['go']
    )
    exercise = Exercise(
        exercise_id=None,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='en',
        language_level=LanguageLevel.A1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data,
    )

    saved_exercise = await repository.create(exercise)
    assert saved_exercise.exercise_id is not None
    assert saved_exercise.exercise_type == exercise.exercise_type
    assert saved_exercise.exercise_language == exercise.exercise_language
    assert saved_exercise.language_level == exercise.language_level
    assert saved_exercise.topic == exercise.topic
    assert saved_exercise.exercise_text == exercise.exercise_text
    assert (
        saved_exercise.data.text_with_blanks == exercise.data.text_with_blanks
    )
    assert saved_exercise.data.words == exercise.data.words
