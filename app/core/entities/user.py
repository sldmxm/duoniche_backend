from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: int
    username: Optional[str] = None
    name: Optional[str] = None
    language_level: str = 'beginner'
    user_language: str = 'Russian'
    target_language: str = 'Bulgarian'
    is_active: bool = True
