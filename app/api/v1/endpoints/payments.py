import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import (
    get_language_config_service,
    get_payment_service,
    get_user_bot_profile_service,
)
from app.api.schemas.payments import (
    PaymentConfirmationRequest,
    PaymentProcessResponse,
)
from app.core.entities.next_action_result import TelegramPayment
from app.core.services.language_config import LanguageConfigService
from app.core.services.payment import DuplicatePaymentError, PaymentService
from app.core.services.user_bot_profile import UserBotProfileService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    '/process',
    response_model=PaymentProcessResponse,
    status_code=status.HTTP_200_OK,
    summary='Process a successful payment',
    description='Generic endpoint to confirm any successful Telegram payment. '
    'It parses the `invoice_payload` to determine the action.',
    tags=['payments'],
)
async def process_payment(
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    payment_data: PaymentConfirmationRequest,
) -> PaymentProcessResponse:
    """
    Processes a successful payment from Telegram.
    This endpoint is generic and handles different payment types based on
    the `invoice_payload`.
    """
    logger.info(
        f'Received payment confirmation. Charge ID: '
        f'{payment_data.telegram_payment_charge_id}, '
        f'Payload: {payment_data.invoice_payload}'
    )

    try:
        await payment_service.process_successful_payment(
            telegram_payment_charge_id=payment_data.telegram_payment_charge_id,
            amount=payment_data.amount,
            currency=payment_data.currency,
            invoice_payload=payment_data.invoice_payload,
            raw_payment_data=payment_data.raw_payment_data,
        )
        message = 'Payment processed successfully.'

    except DuplicatePaymentError:
        logger.warning(
            f'Duplicate payment processing attempt for charge_id: '
            f'{payment_data.telegram_payment_charge_id}. '
            'Payment was already recorded.'
        )
        message = 'Payment already processed.'

    except ValueError as e:
        logger.error(
            f'Invalid payload or parameters for charge_id '
            f'{payment_data.telegram_payment_charge_id}: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid payment payload or data: {str(e)}',
        ) from e

    except Exception as e:
        logger.exception(
            f'An unexpected error occurred while processing payment '
            f'with charge_id: {payment_data.telegram_payment_charge_id}.'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while processing '
            'the payment.',
        ) from e

    return PaymentProcessResponse(status='success', message=message)


@router.get(
    '/invoice-details/{source}/users/{user_id}/bots/{bot_id}',
    response_model=TelegramPayment,
    summary='Get invoice details for various payment types',
    responses={
        status.HTTP_404_NOT_FOUND: {
            'description': 'User or item not found, or item does not '
            'belong to the user.'
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            'description': 'Invalid bot_id or missing item_id for source'
        },
        status.HTTP_400_BAD_REQUEST: {
            'description': 'Unsupported payment source or invalid parameters'
        },
    },
    tags=['payments'],
)
async def get_universal_invoice_details(
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    language_config_service: Annotated[
        LanguageConfigService, Depends(get_language_config_service)
    ],
    source: Annotated[
        str,
        Path(
            description='Payment source '
            '(e.g., "report_donation", "session_unlock")'
        ),
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    bot_id_str: Annotated[
        str,
        Path(alias='bot_id', description='Bot ID (e.g., Bulgarian, English)'),
    ],
    item_id: Annotated[
        Optional[int],
        Query(
            description='ID of the item related to the payment '
            '(e.g., report_id for "report_donation")'
        ),
    ] = None,
) -> TelegramPayment:
    """
    Retrieves payment details required by the bot to display an invoice
    for various payment types (e.g., report donation, session unlock).
    """
    bot_id = bot_id_str
    if bot_id not in language_config_service.get_all_bot_ids():
        logger.warning(f'Invalid bot_id provided: {bot_id_str}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bot_id: '{bot_id_str}'. "
            f'Valid values are: {language_config_service.get_all_bot_ids()}',
        )

    try:
        profile = await user_bot_profile_service.get(
            user_id=user_id, bot_id=bot_id
        )
        if not profile:
            raise ValueError(
                f'No profile found for user {user_id} to get language.'
            )
        user_language = profile.user_language

        payment_details = await payment_service.get_invoice_details_for_source(
            source=source,
            user_id=user_id,
            bot_id=bot_id,
            item_id=item_id,
            user_language=user_language,
        )

        logger.info(
            f'Invoice details retrieved for user {user_id}: {payment_details}'
        )

        return payment_details
    except ValueError as e:
        logger.warning(f'Could not get invoice details for {source}: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.exception(
            f'An unexpected error occurred while getting invoice details for '
            f'source {source}, user {user_id}, bot {bot_id_str}, '
            f'item {item_id}.'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while processing '
            'the request.',
        ) from e
