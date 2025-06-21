from typing import Dict, Optional

from pydantic import BaseModel, Field


class PaymentConfirmationRequest(BaseModel):
    telegram_payment_charge_id: str = Field(
        ..., description='Unique ID of the payment from Telegram'
    )
    amount: int = Field(..., description='Number of stars paid', ge=1)
    invoice_payload: str = Field(..., description='Payload from the invoice')
    currency: str = Field(..., description='Currency of the payment')
    raw_payment_data: Optional[Dict] = Field(
        None, description='Raw payment data from Telegram (JSON)'
    )


class PaymentProcessResponse(BaseModel):
    status: str = 'success'
    message: str = ''
