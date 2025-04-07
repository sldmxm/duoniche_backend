from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.consts import (
    DEFAULT_LANGUAGE_LEVEL,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_USER_LEVEL,
)
from app.core.enums import LanguageLevel


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL
    user_language: str = DEFAULT_USER_LEVEL
    target_language: str = DEFAULT_TARGET_LANGUAGE
    cohort: Optional[str] = None
    plan: Optional[str] = None

    is_active: bool = True

    exercises_get_in_session: int = 0
    exercises_get_in_set: int = 0
    errors_count_in_set: int = 0
    last_exercise_at: Optional[datetime] = None
    session_started_at: Optional[datetime] = None
    session_frozen_until: Optional[datetime] = None
