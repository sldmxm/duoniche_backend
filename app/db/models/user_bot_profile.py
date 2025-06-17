from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.config import settings
from app.core.entities.user_bot_profile import UserStatusInBot
from app.core.enums import LanguageLevel
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class DBUserBotProfile(Base):
    __tablename__ = 'user_bot_profiles'

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('users.user_id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
    )
    bot_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        index=True,
        default=settings.default_target_language,
    )

    user_language: Mapped[str] = mapped_column(String, nullable=False)
    language_level: Mapped[LanguageLevel] = mapped_column(
        SQLAlchemyEnum(
            LanguageLevel, name='language_level_enum', create_type=True
        ),
        nullable=False,
        default=settings.default_language_level,
    )
    status: Mapped[UserStatusInBot] = mapped_column(
        SQLAlchemyEnum(
            UserStatusInBot, name='user_status_in_bot_enum', create_type=True
        ),
        nullable=False,
        default=UserStatusInBot.ACTIVE,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    exercises_get_in_session: Mapped[int] = mapped_column(Integer, default=0)
    exercises_get_in_set: Mapped[int] = mapped_column(Integer, default=0)
    errors_count_in_set: Mapped[int] = mapped_column(Integer, default=0)
    last_exercise_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_frozen_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_streak_days: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    wants_session_reminders: Mapped[bool | None] = mapped_column(
        Boolean, default=None, nullable=True
    )
    last_long_break_reminder_type_sent: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    last_long_break_reminder_sent_at: Mapped[datetime | None] = (
        mapped_column(  # Добавил | None
            DateTime(timezone=True), nullable=True
        )
    )

    last_report_generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_last_calculated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped['User'] = relationship(back_populates='bot_profiles')

    def __repr__(self) -> str:
        return (
            f'<DBUserBotProfile(user_id={self.user_id}, '
            f"bot_id='{self.bot_id.value}', "
            f"status='{self.status.value}')>"
        )
