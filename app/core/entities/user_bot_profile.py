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


class UserBotProfile(BaseModel):
    user_id: int
    bot_id: BotID = Field(default=BotID.BG)

    user_language: str
    language_level: LanguageLevel = Field(default=DEFAULT_LANGUAGE_LEVEL)

    status: UserStatusInBot = Field(default=UserStatusInBot.ACTIVE)
    reason: Optional[str] = None

    exercises_get_in_session: int = 0
    exercises_get_in_set: int = 0
    errors_count_in_set: int = 0
    last_exercise_at: Optional[datetime] = None
    session_started_at: Optional[datetime] = None
    session_frozen_until: Optional[datetime] = None
    updated_at: Optional[datetime] = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
    )
