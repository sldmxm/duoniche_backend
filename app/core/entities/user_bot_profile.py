from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class UserStatusInBot(str, Enum):
    ACTIVE = 'active'
    BLOCKED = 'blocked'
    INACTIVE = 'inactive'


class BotID(str, Enum):
    BG = 'Bulgarian'


class UserBotProfile(BaseModel):
    user_id: int
    bot_id: BotID = Field(default=BotID.BG)
    # user_language: str
    # language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL
    status: UserStatusInBot = Field(default=UserStatusInBot.ACTIVE)
    reason: Optional[str] = None
    # exercises_get_in_session: int = 0
    # exercises_get_in_set: int = 0
    # errors_count_in_set: int = 0
    # last_exercise_at: Optional[datetime] = None
    # session_started_at: Optional[datetime] = None
    # session_frozen_until: Optional[datetime] = None
