from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.models.base import Base


class CachedAnswer(Base):
    __tablename__ = 'cached_answers'

    answer_id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(
        Integer,
        ForeignKey('exercises.exercise_id', ondelete='CASCADE'),
        nullable=False,
    )
    answer = Column(JSONB, nullable=False)
    answer_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    feedback = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by = Column(String)

    exercise = relationship('Exercise', back_populates='cached_answers')
    attempts = relationship(
        'ExerciseAttempt',
        back_populates='cached_answer',
        cascade='all, delete-orphan',
    )
