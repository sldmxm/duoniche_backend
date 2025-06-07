from typing import Optional

from pydantic import BaseModel

from app.core.entities.user_bot_profile import BotID
from app.core.enums import LanguageLevel


class UserPreferencesUpdate(BaseModel):
    wants_reminders: Optional[bool] = None
    language_level: Optional[LanguageLevel] = None


class SessionRemindersPreferenceResponse(BaseModel):
    user_id: int
    bot_id: BotID
    wants_session_reminders: bool
    status: str = 'ok'
