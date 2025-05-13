from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.enums import LanguageLevel


class UserStatusInBot(str, Enum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    INACTIVE = 'inactive'


class BotID(str, Enum):
    BG = 'Bulgarian'
    # SRP = 'Serbian'


class UserBotProfile(BaseModel):
    """
    Represents a user's profile specific to a particular bot (language pair).
    """

    user_id: int = Field(..., description='ID of the associated user')
    bot_id: BotID = Field(
        default=BotID.BG, description='Identifier of the bot (language pair)'
    )

    user_language: str = Field(
        ..., description="User's preferred language code (e.g., 'en', 'ru')"
    )
    language_level: LanguageLevel = Field(
        default=DEFAULT_LANGUAGE_LEVEL,
        description="User's language level in target_language",
    )

    status: UserStatusInBot = Field(default=UserStatusInBot.ACTIVE)
    reason: Optional[str] = None

    exercises_get_in_session: int = Field(
        0,
        description='Number of exercises completed ' 'in the current session',
    )
    exercises_get_in_set: int = Field(
        0, description='Number of exercises completed in the current set'
    )
    errors_count_in_set: int = Field(
        0, description='Number of errors in the current set'
    )
    last_exercise_at: Optional[datetime] = Field(
        None, description='Timestamp of the last completed exercise'
    )
    session_started_at: Optional[datetime] = Field(
        None, description='Timestamp when the current session started'
    )
    session_frozen_until: Optional[datetime] = Field(
        None, description='Timestamp until which the session is frozen'
    )

    wants_session_reminders: Optional[bool] = Field(
        None,
        description='Whether the user wants reminders about '
        'session availability',
    )
    last_long_break_reminder_type_sent: Optional[str] = Field(
        None,
        description='Type/interval of the last long break '
        "reminder sent (e.g., '7d', '30d')",
    )
    last_long_break_reminder_sent_at: Optional[datetime] = Field(
        None, description='Timestamp of the last long break reminder sent'
    )

    model_config = ConfigDict(
        from_attributes=True,
    )
