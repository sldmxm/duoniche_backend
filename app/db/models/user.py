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
    from app.db.models.user_report import UserReport


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    telegram_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=True)
    telegram_data: Mapped[dict] = mapped_column(JSONB, nullable=True)

    cohort: Mapped[str] = mapped_column(String, nullable=True)
    plan: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default='free'
    )
    status_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status_source: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    custom_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now, nullable=False
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

    reports: Mapped[list['UserReport']] = relationship(
        back_populates='user', cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return (
            f"<User(user_id={self.user_id}, telegram_id='{self.telegram_id}')>"
        )
