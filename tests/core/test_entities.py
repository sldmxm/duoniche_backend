from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.value_objects.exercise import (
    SentenceConstructionExerciseData,
)


def test_user_creation():
    user = User(user_id=1, telegram_id=123, username='testuser')
    assert user.user_id == 1
    assert user.telegram_id == 123
    assert user.username == 'testuser'
    assert user.language_level == 'beginner'


def test_exercise_creation():
    exercise = Exercise(
        exercise_id=1,
        exercise_type='sentence_construction',
        language_level='beginner',
        topic='general',
        exercise_text='Make a test sentence.',
        data=SentenceConstructionExerciseData(
            words=['this', 'is', 'a', 'test', 'sentence']
        ),
    )
    assert exercise.exercise_id == 1
    assert exercise.exercise_type == 'sentence_construction'
    assert exercise.language_level == 'beginner'
    assert exercise.topic == 'general'
    assert exercise.exercise_text == 'Make a test sentence.'
    assert exercise.data == SentenceConstructionExerciseData(
        words=['this', 'is', 'a', 'test', 'sentence']
    )


def test_exercise_attempt_creation(
    user, multiple_choice_exercise, sentence_construction_answer
):
    exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=multiple_choice_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
    )
    assert exercise_attempt.attempt_id == 1
    assert exercise_attempt.user_id == user.user_id
