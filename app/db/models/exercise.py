from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.models.base import Base


class Exercise(Base):
    __tablename__ = 'exercises'

    exercise_id = Column(Integer, primary_key=True, index=True)
    exercise_type = Column(String, nullable=False)
    language_level = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    exercise_text = Column(Text, nullable=False)
    data = Column(JSONB, nullable=False)

    attempts = relationship(
        'ExerciseAttempt',
        back_populates='exercise',
        cascade='all, delete-orphan',
    )
    cached_answers = relationship(
        'CachedAnswer', back_populates='exercise', cascade='all, delete-orphan'
    )
