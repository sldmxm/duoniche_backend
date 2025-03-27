from typing import Optional

from pydantic import BaseModel

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.enums import LanguageLevel


class User(BaseModel):
    user_id: Optional[int] = None
    telegram_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL
    user_language: str = 'RU'
    target_language: str = 'BG'
    is_active: bool = True
