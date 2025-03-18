import pytest

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.db.repositories.exercise import SQLAlchemyExerciseRepository

pytestmark = pytest.mark.asyncio


async def test_cached_answer_repository(
    db_session,
    add_db_correct_exercise_answer,
):
    """Test cached answer repository."""
    assert add_db_correct_exercise_answer.answer_id == 1


async def test_exercise_attempt_repository(
    db_session,
    add_db_correct_exercise_answer,
):
    """Test exercise attempt repository."""
    assert add_db_correct_exercise_answer.answer_id == 1


async def test_get_by_id(db_session, sample_exercise):
    """Test getting an exercise by ID."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise = await repository.get_by_id(sample_exercise.exercise_id)
    assert exercise.exercise_id == sample_exercise.exercise_id
    assert exercise.exercise_type == sample_exercise.exercise_type
    assert exercise.exercise_language == sample_exercise.exercise_language
    assert exercise.language_level == sample_exercise.language_level
    assert exercise.topic == sample_exercise.topic
    assert exercise.exercise_text == sample_exercise.exercise_text
    assert (
        exercise.data.text_with_blanks
        == sample_exercise.data['text_with_blanks']
    )
    assert exercise.data.words == sample_exercise.data['words']


async def test_get_by_id_not_found(db_session):
    """Test getting an exercise by ID when it doesn't exist."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise = await repository.get_by_id(99999)
    assert exercise is None


async def test_get_all(db_session, fill_sample_exercises):
    """Test getting all exercises."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercises = await repository.get_all()
    assert len(exercises) == len(fill_sample_exercises)
    for exercise in exercises:
        assert isinstance(exercise, Exercise)


async def get_new_exercise(db_session, get_exercises_by_level, user):
    """Test getting exercises by language level and topic."""
    repository = SQLAlchemyExerciseRepository(db_session)
    language_level = 'A1'
    topic = 'general'
    exercise = await repository.get_new_exercise(
        language_level=language_level,
        topic=topic,
        user=user,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
    )
    assert exercise.language_level == language_level
    assert exercise.topic == topic
    exercise = await repository.get_new_exercise(
        language_level=language_level,
        topic=topic,
        user=user,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
    )
    assert exercise is None


async def test_save(db_session):
    """Test saving a new exercise."""
    repository = SQLAlchemyExerciseRepository(db_session)
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='I ____ to the store.', words=['go']
    )
    exercise = Exercise(
        exercise_id=None,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level='A1',
        topic='general',
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data,
    )

    saved_exercise = await repository.save(exercise)
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
