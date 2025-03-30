from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exercise import Exercise
    from app.db.models.exercise_attempt import ExerciseAttempt


class ExerciseAnswer(Base):
    __tablename__ = 'exercise_answers'

    answer_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey('exercises.exercise_id', ondelete='CASCADE'),
        nullable=False,
    )
    answer: Mapped[dict] = mapped_column(JSONB, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    feedback: Mapped[str | None] = mapped_column(String)
    feedback_language: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String)

    exercise: Mapped['Exercise'] = relationship(
        back_populates='exercise_answers'
    )
    attempts: Mapped[list['ExerciseAttempt']] = relationship(
        back_populates='exercise_answers',
        cascade='all, delete-orphan',
    )
