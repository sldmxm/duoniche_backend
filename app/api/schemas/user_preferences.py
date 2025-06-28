from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.configs.enums import LanguageLevel


class UserPreferencesUpdate(BaseModel):
    wants_reminders: Optional[bool] = None
    language_level: Optional[LanguageLevel] = None
    alphabet: Optional[str] = Field(None, pattern=r'^(latin|cyrillic)$')


class SessionRemindersPreferenceResponse(BaseModel):
    user_id: int
    bot_id: str
    wants_session_reminders: bool
    status: str = 'ok'


class UserBotPreferencesUpdate(BaseModel):
    alphabet: Optional[str] = Field(
        None,
        description=(
            "User's preferred alphabet for the bot "
            "(e.g., 'latin', 'cyrillic')"
        ),
    )


class UserBotPreferencesResponse(BaseModel):
    user_id: int
    bot_id: str
    settings: Dict[str, Any]
