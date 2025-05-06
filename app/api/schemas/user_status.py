from typing import Optional

from pydantic import BaseModel, Field

from app.core.entities.user_bot_profile import BotID


class UserBlockReportPayload(BaseModel):
    bot_id: BotID = Field(default=BotID.BG, description='Blocked bot ID')
    reason: Optional[str] = Field(
        default=None, description='Reason for blocking'
    )
