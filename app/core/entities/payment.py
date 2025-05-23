from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.entities.user_bot_profile import BotID


class Payment(BaseModel):
    """
    Represents a successful payment.
    """

    payment_id: Optional[int] = Field(None, description='Internal payment ID')

    user_id: int = Field(
        ..., description='ID of the user who made the payment'
    )
    bot_id: BotID = Field(
        ..., description='ID of the bot (language pair) the payment is for'
    )

    telegram_payment_charge_id: str = Field(
        ..., description='Unique ID of the payment from Telegram'
    )

    currency: str = Field(..., description='Currency of the payment')
    amount: int = Field(
        ..., description='Amount paid in the specified currency'
    )
    invoice_payload: str = Field(..., description='Payload from the invoice')

    processed_at: Optional[datetime] = Field(
        ...,
        description='Timestamp when the payment was processed by the backend',
    )

    raw_payment_data: Optional[Dict] = Field(
        None, description='Raw payment data from Telegram (JSON)'
    )

    model_config = ConfigDict(
        from_attributes=True,
    )
