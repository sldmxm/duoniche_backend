from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    language_level: Optional[str] = None
    user_language: str = 'RU'
    target_language: str = 'BG'
    is_active: bool = True
