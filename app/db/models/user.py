from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.exercise_attempt import ExerciseAttempt
    from app.db.models.payment import DBPayment
    from app.db.models.user_bot_profile import DBUserBotProfile


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    telegram_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    user_language: Mapped[str] = mapped_column(String, default='ru')
    target_language: Mapped[str] = mapped_column(String, default='bg')
    language_level: Mapped[str] = mapped_column(String, default='A2')
    telegram_data: Mapped[dict] = mapped_column(JSONB, nullable=True)

    cohort: Mapped[str] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, nullable=False
    )

    exercises_get_in_session: Mapped[int] = mapped_column(Integer, default=0)
    exercises_get_in_set: Mapped[int] = mapped_column(Integer, default=0)
    errors_count_in_set: Mapped[int] = mapped_column(Integer, default=0)
    last_exercise_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_frozen_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text)

    attempts: Mapped[list['ExerciseAttempt']] = relationship(
        back_populates='user', cascade='all, delete-orphan'
    )

    bot_profiles: Mapped[list['DBUserBotProfile']] = relationship(
        back_populates='user', cascade='all, delete-orphan'
    )

    payments: Mapped[list['DBPayment']] = relationship(
        back_populates='user', cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return (
            f"<User(user_id={self.user_id}, telegram_id='{self.telegram_id}')>"
        )
