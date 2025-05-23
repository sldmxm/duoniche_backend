from typing import Dict, Optional

from pydantic import BaseModel, Field

from app.core.entities.user_bot_profile import BotID


class PaymentSessionUnlockRequest(BaseModel):
    telegram_payment_charge_id: str = Field(
        ..., description='Unique ID of the payment from Telegram'
    )
    amount: int = Field(..., description='Number of stars paid', ge=1)
    invoice_payload: str = Field(..., description='Payload from the invoice')
    currency: str = Field(..., description='Currency of the payment')
    raw_payment_data: Optional[Dict] = Field(
        None, description='Raw payment data from Telegram (JSON)'
    )


class PaymentSessionUnlockResponse(BaseModel):
    status: str = 'success'
    session_unlocked: bool = True
    message: str = 'Session unlocked successfully.'
    user_id: int
    bot_id: BotID
