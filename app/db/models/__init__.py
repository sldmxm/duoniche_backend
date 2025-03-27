from app.db.base import Base
from app.db.models.exercise import Exercise
from app.db.models.exercise_answer import ExerciseAnswer
from app.db.models.exercise_attempt import ExerciseAttempt
from app.db.models.user import User

__all__ = ['Base', 'Exercise', 'ExerciseAnswer', 'ExerciseAttempt', 'User']

Base.metadata = Base.metadata
