from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseType, LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import (
    SentenceConstructionExerciseData,
)


def test_user_creation():
    user = User(user_id=1, telegram_id='123', username='testuser')
    assert user.user_id == 1
    assert user.telegram_id == '123'
    assert user.username == 'testuser'


def test_exercise_creation():
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='en',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Make a test sentence.',
        data=SentenceConstructionExerciseData(
            words=['this', 'is', 'a', 'test', 'sentence']
        ),
    )
    assert exercise.exercise_id == 1
    assert exercise.exercise_type == ExerciseType.FILL_IN_THE_BLANK
    assert exercise.language_level == LanguageLevel.B1
    assert exercise.topic == ExerciseTopic.GENERAL
    assert exercise.exercise_text == 'Make a test sentence.'
    assert exercise.data == SentenceConstructionExerciseData(
        words=['this', 'is', 'a', 'test', 'sentence']
    )


def test_exercise_attempt_creation():
    answer = FillInTheBlankAnswer(words=['test'])
    attempt = ExerciseAttempt(
        attempt_id=1,
        exercise_id=1,
        user_id=1,
        answer=answer,
        is_correct=True,
        feedback='test',
        answer_id=1,
    )
    assert attempt.attempt_id == 1
    assert attempt.exercise_id == 1
    assert attempt.user_id == 1
    assert attempt.answer == answer
    assert attempt.is_correct is True
    assert attempt.feedback == 'test'
