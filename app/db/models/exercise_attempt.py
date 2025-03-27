from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExerciseAttempt(Base):
    __tablename__ = 'exercise_attempts'

    attempt_id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id = Column(Integer, nullable=False)
    exercise_id = Column(
        Integer,
        ForeignKey('exercises.exercise_id', ondelete='CASCADE'),
        nullable=False,
    )
    answer = Column(JSONB, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    feedback = Column(String)
    exercise_answers_id = Column(
        Integer, ForeignKey('exercise_answers.answer_id', ondelete='SET NULL')
    )

    exercise = relationship('Exercise', back_populates='attempts')
    exercise_answers = relationship(
        'ExerciseAnswer', back_populates='attempts'
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.now(), nullable=False
    )
