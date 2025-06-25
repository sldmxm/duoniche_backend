from typing import Optional

from pydantic import BaseModel

from app.core.configs.enums import LanguageLevel


class UserPreferencesUpdate(BaseModel):
    wants_reminders: Optional[bool] = None
    language_level: Optional[LanguageLevel] = None


class SessionRemindersPreferenceResponse(BaseModel):
    user_id: int
    bot_id: str
    wants_session_reminders: bool
    status: str = 'ok'
