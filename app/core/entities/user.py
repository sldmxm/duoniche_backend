from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.core.consts import (
    DEFAULT_LANGUAGE_LEVEL,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_USER_LANGUAGE,
)
from app.core.enums import LanguageLevel


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    telegram_data: Optional[dict] = None
    cohort: Optional[str] = None
    plan: Optional[str] = None
    is_active: bool = True

    # TODO: Remove after moving to user_bot_profile
    language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL
    user_language: str = DEFAULT_USER_LANGUAGE
    target_language: str = DEFAULT_TARGET_LANGUAGE

    exercises_get_in_session: int = 0
    exercises_get_in_set: int = 0
    errors_count_in_set: int = 0
    last_exercise_at: Optional[datetime] = None
    session_started_at: Optional[datetime] = None
    session_frozen_until: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
    )
