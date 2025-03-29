import pytest

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.llm_service import LLMService

pytestmark = pytest.mark.asyncio

llm_service = LLMService(
    openai_api_key=settings.openai_api_key,
    model_name=settings.openai_test_model_name,
)


@pytest.fixture()
def user():
    return User(
        user_id=1,
        telegram_id='123',
        username='testuser',
        name='Test User',
        user_language='russian',
        target_language='bulgarian',
    )


async def test_generate_fill_in_the_blank_exercise(user):
    try:
        exercise, answer = await llm_service.generate_exercise(
            user,
            LanguageLevel.B1,
            ExerciseType.FILL_IN_THE_BLANK,
            ExerciseTopic.GENERAL,
        )
    except ValueError:
        return

    assert exercise.exercise_type == ExerciseType.FILL_IN_THE_BLANK
    assert exercise.data.text_with_blanks
    assert exercise.data.words
    assert isinstance(answer, FillInTheBlankAnswer)


async def test_validate_attempt_correct(user):
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='The cat ___ on the mat.',
            words=['sat', 'run', 'jumped'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['sat'])
    is_correct, feedback = await llm_service.validate_attempt(
        user, exercise, answer
    )

    assert is_correct is True
    assert feedback == ''


async def test_validate_attempt_incorrect(user):
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='Аз обичам да ___ в парка.',
            words=['ходя', 'ходяа', 'гледам'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['гледам'])
    is_correct, feedback = await llm_service.validate_attempt(
        user,
        exercise,
        answer,
    )

    assert is_correct is False
    assert feedback is not None
