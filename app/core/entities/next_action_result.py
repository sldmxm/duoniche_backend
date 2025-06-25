from datetime import timedelta
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.core.configs.enums import UserAction
from app.core.entities.exercise import Exercise


class TelegramPaymentItem(BaseModel):
    label: str
    amount: int


class TelegramPayment(BaseModel):
    button_text: str
    title: str
    description: str
    currency: str
    prices: List[TelegramPaymentItem]
    thanks_answer: str
    invoice_payload: Optional[str] = None


class NextAction(BaseModel):
    action: UserAction
    exercise: Optional[Exercise] = None
    message: Optional[str] = None
    pause: Optional[timedelta] = None
    keyboard: Optional[List[Dict[str, str]]] = None
