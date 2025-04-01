from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exercise import Exercise
    from app.db.models.exercise_answer import ExerciseAnswer
    from app.db.models.user import User


class ExerciseAttempt(Base):
    __tablename__ = 'exercise_attempts'

    attempt_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey('exercises.exercise_id', ondelete='CASCADE'),
        nullable=False,
    )
    answer: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String)
    answer_id: Mapped[int | None] = mapped_column(
        ForeignKey('exercise_answers.answer_id', ondelete='SET NULL')
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, nullable=False
    )

    user: Mapped['User'] = relationship(back_populates='attempts')
    exercise: Mapped['Exercise'] = relationship(back_populates='attempts')
    exercise_answers: Mapped['ExerciseAnswer'] = relationship(
        back_populates='attempts'
    )
