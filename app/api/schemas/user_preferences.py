from pydantic import BaseModel

from app.core.entities.user_bot_profile import BotID


class SessionRemindersPreferenceUpdate(BaseModel):
    wants_reminders: bool


class SessionRemindersPreferenceResponse(BaseModel):
    user_id: int
    bot_id: BotID
    wants_session_reminders: bool
    status: str = 'ok'
