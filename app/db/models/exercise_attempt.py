from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExerciseAttempt(Base):
    __tablename__ = 'exercise_attempts'

    attempt_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    exercise_id = Column(
        Integer,
        ForeignKey('exercises.exercise_id', ondelete='CASCADE'),
        nullable=False,
    )
    answer = Column(JSONB, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    feedback = Column(String)
    cached_answer_id = Column(
        Integer, ForeignKey('cached_answers.answer_id', ondelete='SET NULL')
    )

    exercise = relationship('Exercise', back_populates='attempts')
    cached_answer = relationship('CachedAnswer', back_populates='attempts')
