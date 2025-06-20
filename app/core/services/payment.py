import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.core.entities.next_action_result import (
    TelegramPayment,
    TelegramPaymentItem,
)
from app.core.entities.payment import Payment
from app.core.entities.user_bot_profile import BotID
from app.core.repositories.payment import PaymentRepository
from app.core.texts import PaymentMessages, get_text

logger = logging.getLogger(__name__)


class DuplicatePaymentError(ValueError):
    """Custom exception for attempting to process a duplicate payment."""

    def __init__(self, telegram_payment_charge_id: str):
        self.telegram_payment_charge_id = telegram_payment_charge_id
        super().__init__(
            f'Payment with telegram_payment_charge_id '
            f"'{telegram_payment_charge_id}' already exists."
        )


class PaymentService:
    def __init__(self, payment_repository: PaymentRepository):
        self._payment_repository = payment_repository

    def get_payment_unlock_details(
        self, user_language: str
    ) -> TelegramPayment:
        payment_tiers = [
            (20, PaymentMessages.ITEM_LABEL_TIER_1),
            (50, PaymentMessages.ITEM_LABEL_TIER_2),
            (100, PaymentMessages.ITEM_LABEL_TIER_3),
            (200, PaymentMessages.ITEM_LABEL_TIER_4),
            (500, PaymentMessages.ITEM_LABEL_TIER_5),
            (1000, PaymentMessages.ITEM_LABEL_TIER_6),
        ]
        prices = []
        for amount, label_key in payment_tiers:
            prices.append(
                TelegramPaymentItem(
                    label=get_text(label_key, user_language),
                    amount=amount,
                )
            )
        if not prices:
            logger.warning(
                'No payment tiers available after filtering, '
                'adding a default.'
            )
            prices.append(
                TelegramPaymentItem(
                    label=get_text(PaymentMessages.ITEM_LABEL, user_language),
                    amount=settings.min_session_unlock_payment,
                )
            )

        payment_details = TelegramPayment(
            button_text=get_text(PaymentMessages.BUTTON_TEXT, user_language),
            title=get_text(PaymentMessages.TITLE, user_language),
            description=get_text(PaymentMessages.DESCRIPTION, user_language),
            currency='XTR',
            prices=prices,
            thanks_answer=get_text(
                PaymentMessages.THANKS_ANSWER, user_language
            ),
        )
        return payment_details

    async def record_successful_payment(
        self,
        user_id: int,
        bot_id: BotID,
        telegram_payment_charge_id: str,
        amount: int,
        currency: str,
        invoice_payload: str,
        raw_payment_data: Optional[dict] = None,
    ) -> Payment:
        """
        Records a successful payment after verifying it's not a duplicate.

        Args:
            user_id: The internal ID of the user.
            bot_id: The BotID for which the payment was made.
            telegram_payment_charge_id: The unique charge ID from Telegram.
            amount: The amount paid.
            currency: The currency of the payment (e.g., "XTR").
            invoice_payload: The payload from the invoice.
            raw_payment_data: Optional raw payment data from Telegram (JSON)

        Returns:
            The created Payment entity.

        Raises:
            DuplicatePaymentError: If a payment with the same
                                telegram_payment_charge_id already exists.
        """
        existing_payment = (
            await self._payment_repository.get_payment_by_charge_id(
                telegram_payment_charge_id
            )
        )
        if existing_payment:
            logger.warning(
                f'Attempt to record a duplicate payment with charge_id: '
                f'{telegram_payment_charge_id}'
            )
            raise DuplicatePaymentError(telegram_payment_charge_id)

        payment_to_create = Payment(
            payment_id=None,
            user_id=user_id,
            bot_id=bot_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            amount=amount,
            currency=currency,
            invoice_payload=invoice_payload,
            processed_at=datetime.now(timezone.utc),
            raw_payment_data=raw_payment_data,
        )

        created_payment = await self._payment_repository.create_payment(
            payment_to_create
        )
        logger.info(
            f'Successfully recorded payment {created_payment.payment_id} '
            f'(Charge ID: {telegram_payment_charge_id}) for user {user_id}.'
        )
        return created_payment

    async def get_payment_by_charge_id(
        self, telegram_payment_charge_id: str
    ) -> Payment | None:
        """
        Retrieves a payment by its Telegram payment charge ID.
        """
        return await self._payment_repository.get_payment_by_charge_id(
            telegram_payment_charge_id
        )
