from typing import Optional

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    telegram_data: Optional[dict] = None
    cohort: Optional[str] = None
    plan: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True,
    )
