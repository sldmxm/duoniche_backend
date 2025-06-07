import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import (
    get_payment_service,
    get_user_bot_profile_service,
    get_user_service,
)
from app.api.errors import NotFoundError
from app.api.schemas.payments import (
    PaymentSessionUnlockRequest,
    PaymentSessionUnlockResponse,
)
from app.api.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.api.schemas.user_preferences import (
    SessionRemindersPreferenceResponse,
    UserPreferencesUpdate,
)
from app.api.schemas.user_status import (
    ReportBlockResponse,
    UserBlockReportPayload,
)
from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.services.payment import DuplicatePaymentError, PaymentService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.metrics import BACKEND_PAYMENT_METRICS, BACKEND_USER_METRICS

logger = logging.getLogger(__name__)
router = APIRouter()


@router.put(
    '/',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_or_create_user(
    user_data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
) -> UserResponse:
    """
    Get or create a user.
    """
    # TODO: Переписать на users/bots/{bot_id}
    try:
        user = User(
            telegram_id=user_data.telegram_id,
            username=user_data.username,
            name=user_data.name,
            telegram_data=user_data.telegram_data,
        )
        user_from_service, is_created = await user_service.get_or_create(user)

        try:
            bot_id = BotID(user_data.target_language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f'Invalid target_language: '
                    f"'{user_data.target_language}'. "
                    f'Valid values are: '
                    f'{[member.value for member in BotID]}'
                ),
            ) from e

        if user_from_service and user_from_service.user_id:
            user_bot_profile, _ = await user_bot_profile_service.get_or_create(
                user_id=user_from_service.user_id,
                bot_id=bot_id,
                user_language=user_data.user_language,
                language_level=settings.default_language_level,
            )
        else:
            raise ValueError('User not found')

        if is_created:
            BACKEND_USER_METRICS['new'].labels(
                cohort=user_from_service.cohort,
                plan=user_from_service.plan,
                target_language=user_data.target_language,
                user_language=user_bot_profile.user_language,
                language_level=user_bot_profile.language_level.value,
            ).inc()

        output = _create_user_for_response(
            user=user_from_service,
            user_bot_profile=user_bot_profile,
        )

    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e

    return output


@router.get(
    '/by-telegram-id/{telegram_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_by_telegram_id(
    telegram_id: str,
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    bot_id_str: Annotated[Optional[str], Query(alias='bot_id')] = None,
) -> UserResponse:
    """
    Get user by telegram_id, optionally for a specific bot_id.
    If bot_id is not provided, tries to find any existing bot profile.
    """
    user = await user_service.get_by_telegram_id(telegram_id)
    if not user or not user.user_id:
        raise NotFoundError(detail='User not found')

    if bot_id_str:
        try:
            bot_id = BotID(bot_id_str)
            user_bot_profile = await user_bot_profile_service.get(
                user.user_id, bot_id
            )
            if not user_bot_profile:
                raise NotFoundError(
                    detail=f'Bot profile for bot_id {bot_id_str} '
                    f'not found for user {telegram_id}'
                )
        except ValueError as e:
            valid_bot_ids = [member.value for member in BotID]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bot_id: '{bot_id_str}'. "
                f'Valid values are: {valid_bot_ids}',
            ) from e
    else:
        profiles = await user_bot_profile_service.get_all_by_user_id(
            user.user_id
        )
        if profiles and profiles[0]:
            user_bot_profile = profiles[0]
        else:
            raise NotFoundError(
                detail=f'No bot profiles found for user {telegram_id}. '
                f'Please specify a bot_id or ensure a profile exists.'
            )

    if not user_bot_profile:
        raise NotFoundError(
            detail=f'Could not determine bot profile for user {telegram_id}.'
        )

    return _create_user_for_response(
        user=user, user_bot_profile=user_bot_profile
    )


@router.put(
    '/{user_id}',
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def update_user_by_user_id(
    user_id: int,
    user_data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
) -> UserResponse:
    """
    Update user by user_id.
    """
    try:
        updated_user = await user_service.update(
            user_id=user_id,
            username=user_data.username,
            name=user_data.name,
            telegram_data=user_data.telegram_data,
        )

        try:
            bot = BotID(user_data.target_language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f'Invalid target_language: '
                    f"'{user_data.target_language}'. "
                    f'Valid values are: {[member.value for member in BotID]}'
                ),
            ) from e

        updated_user_bot_profile = (
            await user_bot_profile_service.update_profile(
                user_id=user_id,
                bot_id=bot,
                user_language=user_data.user_language,
            )
        )
        output = _create_user_for_response(
            user=updated_user,
            user_bot_profile=updated_user_bot_profile,
        )
    except ValueError as e:
        raise NotFoundError(detail=str(e)) from e
    return output


@router.post(
    '/{user_id}/bots/{bot_id}/block',
    response_model=ReportBlockResponse,
    summary='Set bot as blocked by user',
    description='Set bot as blocked by user',
)
async def block_bot(
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    bot_id: Annotated[
        BotID, Path(description='Bot ID (e.g., Bulgarian, English)')
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    report: UserBlockReportPayload,
):
    user = await user_service.get_by_id(user_id)
    if not user or user.telegram_id != report.telegram_id:
        raise NotFoundError(detail='User not found')
    try:
        await user_bot_profile_service.mark_user_blocked(
            user_id=user_id, bot_id=bot_id, reason=report.reason
        )
    except ValueError as e:
        logger.error(f'Invalid parameter value: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Invalid parameter value: {str(e)}',
        ) from e

    return ReportBlockResponse(status='ok')


def _create_user_for_response(
    user: User, user_bot_profile: UserBotProfile
) -> UserResponse:
    if not user or not user_bot_profile or not user.user_id:
        raise ValueError('User not found')
    return UserResponse(
        user_id=user.user_id,
        telegram_id=user.telegram_id,
        username=user.username,
        name=user.name,
        telegram_data=user.telegram_data,
        plan=user.plan,
        status=user.status,
        status_expires_at=user.status_expires_at,
        cohort=user.cohort,
        user_language=user_bot_profile.user_language,
        language_level=user_bot_profile.language_level.value,
    )


@router.put(
    '/{user_id}/bots/{bot_id}/preferences/session_reminders',
    response_model=SessionRemindersPreferenceResponse,
    summary="Update user's session reminder preference for a bot",
    status_code=status.HTTP_200_OK,
)
async def update_session_reminders_preference(
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    bot_id: Annotated[
        BotID, Path(description='Bot ID (e.g., Bulgarian, English)')
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    preference_data: UserPreferencesUpdate,
):
    user = await user_service.get_by_id(user_id)
    if not user:
        raise NotFoundError(detail=f'User with id {user_id} not found')

    try:
        updated_profile = await user_bot_profile_service.update_profile(
            user_id=user_id,
            bot_id=bot_id,
            wants_session_reminders=preference_data.wants_reminders,
        )
    except ValueError as e:
        logger.error(
            f'Error updating session reminder preference for '
            f'user {user_id}, bot {bot_id.value}: {e}'
        )
        raise NotFoundError(detail=str(e)) from e
    except Exception as e:
        logger.error(
            f'Unexpected error updating session reminder '
            f'preference for user {user_id}, bot {bot_id.value}: {e}',
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while updating preferences.',
        ) from e

    wants_session_reminders = updated_profile.wants_session_reminders is True

    logger.info(
        f'Updated session reminders to '
        f'{wants_session_reminders} preference '
        f'for User {updated_profile.user_id}/{updated_profile.bot_id}'
    )

    BACKEND_USER_METRICS['set_session_reminder'].labels(
        cohort=user.cohort,
        plan=user.plan,
        target_language=updated_profile.bot_id,
        user_language=updated_profile.user_language,
        language_level=updated_profile.language_level.value,
        wants_session_reminders=wants_session_reminders,
    ).inc()

    return SessionRemindersPreferenceResponse(
        user_id=updated_profile.user_id,
        bot_id=updated_profile.bot_id,
        wants_session_reminders=wants_session_reminders,
    )


@router.post(
    '/{user_id}/bots/{bot_id}/payments/unlock-session',
    response_model=PaymentSessionUnlockResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlock user's session after a successful payment",
    tags=['users', 'payments'],
)
async def process_payment_unlock_session(
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    user_id: Annotated[
        int, Path(description='User ID from your database', ge=1)
    ],
    bot_id_str: Annotated[
        str,
        Path(alias='bot_id', description='Bot ID (e.g., Bulgarian, English)'),
    ],
    donation_data: PaymentSessionUnlockRequest,
):
    """
    Processes a successful payment to unlock the user's next
    session immediately.
    The bot should call this endpoint after receiving
    a SuccessfulPayment from Telegram.
    """
    try:
        bot_id = BotID(bot_id_str)
    except ValueError as e:
        logger.warning(
            f"Invalid bot_id '{bot_id_str}' in path for user {user_id} "
            f'during payment processing.'
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid bot_id in path: '{bot_id_str}'. "
                f'Valid values are: {[member.value for member in BotID]}'
            ),
        ) from e

    user = await user_service.get_by_id(user_id)
    if not user:
        logger.error(
            f'User not found for ID {user_id} during payment processing.'
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'User with ID {user_id} not found.',
        )
    user_profile_for_metrics = await user_bot_profile_service.get(
        user_id, bot_id
    )
    if not user_profile_for_metrics:
        logger.error(
            f'UserBotProfile not found for user {user_id}, '
            f'bot {bot_id.value} during payment processing.'
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Profile for user {user_id}, '
            f'bot {bot_id.value} not found.',
        )

    metric_labels = {
        'cohort': user.cohort,
        'plan': user.plan,
        'target_language': bot_id.value,
        'user_language': user_profile_for_metrics.user_language,
        'language_level': user_profile_for_metrics.language_level.value,
    }

    logger.info(
        f'Attempting to process payment to unlock session for user_id: '
        f'{user_id}, bot_id: {bot_id.value}. Charge ID: '
        f'{donation_data.telegram_payment_charge_id}'
    )

    payment_recorded_successfully = False
    try:
        recorded_payment = await payment_service.record_successful_payment(
            user_id=user_id,
            bot_id=bot_id,
            telegram_payment_charge_id=donation_data.telegram_payment_charge_id,
            amount=donation_data.amount,
            currency=donation_data.currency,
            invoice_payload=donation_data.invoice_payload,
            raw_payment_data=donation_data.raw_payment_data,
        )
        payment_recorded_successfully = True

        payment_amount_labels = {
            **metric_labels,
            'currency': recorded_payment.currency,
        }
        BACKEND_PAYMENT_METRICS['amount_total'].labels(
            **payment_amount_labels
        ).inc(recorded_payment.amount)

    except DuplicatePaymentError:
        logger.warning(
            f'Duplicate payment processing attempt for charge_id: '
            f'{donation_data.telegram_payment_charge_id} for user {user_id}. '
            f'Payment already recorded. Proceeding to unlock session.'
        )
    except Exception as e:
        logger.exception(
            f'Failed to record payment for user {user_id}, '
            f'charge_id: {donation_data.telegram_payment_charge_id}.'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An error occurred while recording the payment. '
            'Session not unlocked.',
        ) from e

    try:
        updated_profile = (
            await user_bot_profile_service.reset_and_start_new_session(
                user_id=user_id, bot_id=bot_id
            )
        )

        BACKEND_USER_METRICS['session_unlocked_by_payment'].labels(
            **metric_labels
        ).inc()

        logger.info(
            f'Session successfully unlocked for user {user_id}, '
            f'bot {bot_id.value} after payment '
            f'{donation_data.telegram_payment_charge_id}.'
        )
    except ValueError as e:
        logger.error(
            f'Failed to unlock session for user {user_id}, '
            f'bot {bot_id.value} after payment processing: {e}'
        )
        detail_msg = (
            f'Payment recorded, but could not unlock session for '
            f'user {user_id}, bot {bot_id.value}. Details: {str(e)}'
        )
        if not payment_recorded_successfully:
            detail_msg = (
                f'Could not unlock session for user {user_id}, '
                f'bot {bot_id.value} (payment was a duplicate '
                f'or not processed). '
                f'Details: {str(e)}'
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        ) from e
    except Exception as e:
        logger.exception(
            f'Unexpected error unlocking session for user '
            f'{user_id}, bot {bot_id.value} after payment processing.'
        )
        detail_msg = (
            'Payment recorded, but an unexpected error occurred '
            'while unlocking the session.'
        )
        if not payment_recorded_successfully:
            detail_msg = (
                'An unexpected error occurred while unlocking the session '
                '(payment was a duplicate or not processed).'
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail_msg,
        ) from e

    return PaymentSessionUnlockResponse(
        user_id=updated_profile.user_id,
        bot_id=updated_profile.bot_id,
        message=f'New session for user {user_id}, bot {bot_id.value} '
        f'started successfully after payment.',
    )
