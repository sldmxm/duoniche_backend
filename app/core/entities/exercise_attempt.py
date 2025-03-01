from dataclasses import dataclass

from app.core.value_objects.answer import Answer


@dataclass
class ExerciseAttempt:
    attempt_id: int
    exercise_id: int
    user_id: int
    answer: Answer
    is_correct: bool
    feedback: str | None = None
    correct_answer_id: int | None = None
