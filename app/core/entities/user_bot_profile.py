from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings
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
        default=settings.default_language_level,
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
    current_streak_days: int = Field(
        default=0, description='Current number of consecutive days of activity'
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

    last_report_generated_at: Optional[datetime] = Field(
        None, description='Timestamp of the last report generation'
    )

    rating: Optional[float] = Field(
        None, description="User's calculated rating for this bot/language"
    )
    rating_last_calculated_at: Optional[datetime] = Field(
        None, description='Timestamp when the rating was last calculated'
    )

    settings: Optional[Dict] = Field(
        None,
        description='Bot-specific custom settings overrides, '
        'e.g., exercise distribution.',
    )

    @field_validator('bot_id', mode='before')
    @classmethod
    def validate_bot_id(cls, v):
        if isinstance(v, str):
            for bot in BotID:
                if bot.value == v:
                    return bot
            raise ValueError(f'Invalid bot_id value: {v}')
        return v

    model_config = ConfigDict(
        from_attributes=True,
    )
