from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.core.configs.enums import UserStatus
from app.core.entities.user_settings import UserCustomSettings


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    telegram_data: Optional[dict] = None
    cohort: Optional[str] = None
    plan: Optional[str] = None  # Deprecated in favor of status
    status: UserStatus = UserStatus.FREE
    status_expires_at: Optional[datetime] = None
    status_source: Optional[str] = None
    custom_settings: Optional[UserCustomSettings] = None
    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True,
    )
