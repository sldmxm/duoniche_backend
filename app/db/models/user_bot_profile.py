from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.entities.user_bot_profile import BotID, UserStatusInBot
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
    bot_id: Mapped[BotID] = mapped_column(
        SQLAlchemyEnum(BotID, name='bot_id_enum', create_type=True),
        primary_key=True,
        index=True,
        default=BotID.BG,
    )

    user_language: Mapped[str] = mapped_column(String, nullable=False)
    language_level: Mapped[LanguageLevel] = mapped_column(
        SQLAlchemyEnum(
            LanguageLevel, name='language_level_enum', create_type=True
        ),
        nullable=False,
        default=DEFAULT_LANGUAGE_LEVEL,
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
