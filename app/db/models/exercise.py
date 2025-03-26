from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Exercise(Base):
    __tablename__ = 'exercises'

    exercise_id = Column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    exercise_type = Column(String, nullable=False)
    exercise_language = Column(String, nullable=False)
    language_level = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    exercise_text = Column(Text, nullable=False)
    data = Column(JSONB, nullable=False)

    attempts = relationship(
        'ExerciseAttempt',
        back_populates='exercise',
        cascade='all, delete-orphan',
    )
    exercise_answers = relationship(
        'ExerciseAnswer',
        back_populates='exercise',
        cascade='all, delete-orphan',
    )
    created_at = Column(
        DateTime(timezone=True), default=datetime.now(), nullable=False
    )
