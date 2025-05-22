from datetime import timedelta
from typing import List, Optional

from pydantic import BaseModel

from app.core.entities.exercise import Exercise
from app.core.enums import UserAction


class TelegramPaymentItem(BaseModel):
    label: str
    amount: int


class TelegramPayment(BaseModel):
    button_text: str
    title: str
    description: str
    provider_token: str = ''
    currency: str
    prices: List[TelegramPaymentItem]
    thanks_answer: str


class NextAction(BaseModel):
    action: UserAction
    exercise: Optional[Exercise] = None
    message: Optional[str] = None
    pause: Optional[timedelta] = None
    payment_info: Optional[TelegramPayment] = None
