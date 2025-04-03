from datetime import timedelta
from typing import Optional

from pydantic import BaseModel

from app.core.entities.exercise import Exercise
from app.core.enums import UserAction


class NextAction(BaseModel):
    action: UserAction
    exercise: Optional[Exercise] = None
    message: Optional[str] = None
    pause: Optional[timedelta] = None
