from datetime import timedelta
from typing import Optional

from pydantic import BaseModel

from app.api.schemas.exercise import ExerciseSchema
from app.core.entities.next_action_result import TelegramPayment
from app.core.enums import UserAction


class NextActionSchema(BaseModel):
    exercise: Optional[ExerciseSchema] = None
    action: UserAction
    message: Optional[str] = None
    pause: Optional[timedelta] = None
    payment_info: Optional[TelegramPayment] = None
