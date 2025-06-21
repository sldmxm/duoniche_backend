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
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_report import UserReportService
from app.core.texts import PaymentMessages, get_text

logger = logging.getLogger(__name__)

INVOICE_PAYLOAD_PREFIX = 'invoice_payload_prefix'


class DuplicatePaymentError(ValueError):
    """Custom exception for attempting to process a duplicate payment."""

    def __init__(self, telegram_payment_charge_id: str):
        self.telegram_payment_charge_id = telegram_payment_charge_id
        super().__init__(
            f'Payment with telegram_payment_charge_id '
            f"'{telegram_payment_charge_id}' already exists."
        )


class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        user_bot_profile_service: UserBotProfileService,
        user_report_service: UserReportService,
    ):
        self._payment_repository = payment_repository
        self._user_bot_profile_service = user_bot_profile_service
        self._user_report_service = user_report_service
        self.payment_source_actions = {
            'session_unlock': self._handle_session_unlock,
        }

    def _get_invoice_payload(
        self,
        source: str,
        user_id: int,
        bot_id: BotID,
        item_id: int,
    ):
        invoice_payload = (
            f'{INVOICE_PAYLOAD_PREFIX}'
            f':{source}'
            f':{user_id}'
            f':{bot_id.value}'
            f':{item_id}'
            f'_time_{int(datetime.now(timezone.utc).timestamp())}'
        )
        return invoice_payload

    def _parse_get_invoice_payload(self, invoice_payload: str):
        if not invoice_payload.startswith(INVOICE_PAYLOAD_PREFIX):
            raise ValueError(
                f'Invalid invoice_payload format: {invoice_payload}'
            )

        payload_parts = invoice_payload.split(':')
        source = payload_parts[1]
        if source not in ('report_donation', 'session_unlock'):
            raise ValueError(f'Unknown payment source: {source}')

        user_id = int(payload_parts[2])

        bot_id_str = payload_parts[3]
        try:
            bot_id = BotID(bot_id_str)
        except ValueError as e:
            raise ValueError(f'Invalid bot_id: {bot_id_str}') from e

        item_id = int(payload_parts[4])

        return source, user_id, bot_id, item_id

    def get_unlock_payment_details(
        self,
        user_id: int,
        bot_id: BotID,
        user_language: str,
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
                    amount=settings.min_session_unlock_payment_xtr,
                )
            )
        invoice_payload = self._get_invoice_payload(
            source='session_unlock',
            user_id=user_id,
            bot_id=bot_id,
            item_id=-1,
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
            invoice_payload=invoice_payload,
        )
        return payment_details

    async def get_report_donation_details(
        self,
        user_id: int,
        bot_id: BotID,
        report_id: int,
        user_language: str,
    ) -> TelegramPayment:
        report = await self._user_report_service.get_by_id_and_user(
            report_id=report_id, user_id=user_id
        )
        if not report:
            raise ValueError(
                f'Report {report_id} not found for user {user_id}.'
            )

        invoice_payload = self._get_invoice_payload(
            source='report_donation',
            user_id=user_id,
            bot_id=bot_id,
            item_id=report_id,
        )

        price_item = TelegramPaymentItem(
            label=get_text(
                PaymentMessages.ITEM_LABEL_TIER_2, language_code=user_language
            ),
            amount=settings.report_donation_amount_xtr,
        )

        payment_details = TelegramPayment(
            button_text=get_text(
                PaymentMessages.REPORT_DONATION_BUTTON_TEXT, user_language
            ),
            title=get_text(PaymentMessages.TITLE, user_language),
            description=get_text(PaymentMessages.DESCRIPTION, user_language),
            currency='XTR',
            prices=[price_item],
            thanks_answer=get_text(
                PaymentMessages.THANKS_ANSWER, user_language
            ),
            invoice_payload=invoice_payload,
        )

        return payment_details

    async def get_invoice_details_for_source(
        self,
        source: str,
        user_id: int,
        bot_id: BotID,
        user_language: str,
        item_id: Optional[int] = None,
    ) -> TelegramPayment:
        """
        Retrieves payment details for a given source.
        This acts as a dispatcher to specific payment detail getters.
        """
        if source == 'report_donation':
            if item_id is None:
                raise ValueError(
                    'item_id (report_id) is required for '
                    "'report_donation' source."
                )
            return await self.get_report_donation_details(
                user_id=user_id,
                bot_id=bot_id,
                report_id=item_id,
                user_language=user_language,
            )
        elif source == 'session_unlock':
            return self.get_unlock_payment_details(
                user_id=user_id,
                bot_id=bot_id,
                user_language=user_language,
            )
        else:
            raise ValueError(f'Unsupported payment source: {source}')

    async def process_successful_payment(
        self,
        telegram_payment_charge_id: str,
        amount: int,
        currency: str,
        invoice_payload: str,
        raw_payment_data: Optional[dict] = None,
    ) -> Payment:
        existing_payment = (
            await self._payment_repository.get_payment_by_charge_id(
                telegram_payment_charge_id
            )
        )
        if existing_payment:
            raise DuplicatePaymentError(telegram_payment_charge_id)

        source, user_id, bot_id, item_id = self._parse_get_invoice_payload(
            invoice_payload
        )

        if source == 'report_donation':
            report_id = item_id
            report = await self._user_report_service.get_by_id(report_id)
            if not report:
                raise ValueError(f'Report not found for report_id {report_id}')

        payment_to_create = Payment(
            user_id=user_id,
            bot_id=bot_id,
            source=source,
            telegram_payment_charge_id=telegram_payment_charge_id,
            amount=amount,
            currency=currency,
            invoice_payload=invoice_payload,
            processed_at=datetime.now(timezone.utc),
            raw_payment_data=raw_payment_data,
            payment_id=None,
        )

        created_payment = await self._payment_repository.create_payment(
            payment_to_create
        )
        logger.info(
            f'Successfully recorded payment {created_payment.payment_id} for '
            f'user {user_id}, source: {source}. Charge ID: '
            f'{telegram_payment_charge_id}.'
        )

        if source in self.payment_source_actions:
            await self.payment_source_actions[source](
                user_id=user_id,
                bot_id=bot_id,
                item_id=item_id,
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

    async def _handle_session_unlock(
        self, user_id: int, bot_id: BotID, *args, **kwargs
    ) -> None:
        """
        Handles the post-payment action for a session unlock.
        """
        logger.info(
            f'Unlocking session for user {user_id}, bot {bot_id.value}.'
        )

        await self._user_bot_profile_service.reset_and_start_new_session(
            user_id=user_id, bot_id=bot_id
        )

        # TODO: И отправить следующее задание? Хотя, это бот должен запросить
        #  сразу
