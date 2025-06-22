import logging
from typing import Optional, override

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entities.payment import Payment as CorePayment
from app.core.repositories.payment import (
    PaymentRepository as PaymentRepositoryProtocol,
)
from app.db.models.payment import DBPayment

logger = logging.getLogger(__name__)


class SQLAlchemyPaymentRepository(PaymentRepositoryProtocol):
    def __init__(self, session: AsyncSession):
        self.session = session

    @override
    async def create_payment(self, payment_data: CorePayment) -> CorePayment:
        """
        Creates a new payment record in the database.
        """
        db_payment = DBPayment(
            user_id=payment_data.user_id,
            bot_id=payment_data.bot_id,
            telegram_payment_charge_id=payment_data.telegram_payment_charge_id,
            currency=payment_data.currency,
            amount=payment_data.amount,
            invoice_payload=payment_data.invoice_payload,
            processed_at=payment_data.processed_at,
            raw_payment_data=payment_data.raw_payment_data,
            source=payment_data.source,
        )
        self.session.add(db_payment)
        try:
            await self.session.flush()
            await self.session.refresh(db_payment)
        except IntegrityError as e:
            if 'payments_telegram_payment_charge_id_key' in str(e.orig):
                logger.warning(
                    f'Attempted to create a payment with duplicate '
                    f'telegram_payment_charge_id: '
                    f'{payment_data.telegram_payment_charge_id}. Error: {e}'
                )
            else:
                logger.error(f'Error creating DBPayment: {e}', exc_info=True)
            raise
        except Exception as e:
            logger.error(
                f'Unexpected error creating DBPayment: {e}', exc_info=True
            )
            raise

        return CorePayment.model_validate(db_payment)

    @override
    async def get_payment_by_charge_id(
        self, telegram_payment_charge_id: str
    ) -> Optional[CorePayment]:
        """
        Retrieves a payment by its Telegram payment charge ID.
        """
        stmt = select(DBPayment).where(
            DBPayment.telegram_payment_charge_id == telegram_payment_charge_id
        )
        result = await self.session.execute(stmt)
        db_payment = result.scalar_one_or_none()

        if db_payment:
            return CorePayment.model_validate(db_payment)
        return None
