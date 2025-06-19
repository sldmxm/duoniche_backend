import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_detailed_report_service,
    get_payment_service,
    get_user_bot_profile_service,
)
from app.api.schemas.next_action_result import NextActionSchema
from app.api.schemas.report import ReportNotFound
from app.core.entities.user_bot_profile import BotID
from app.core.enums import UserAction
from app.core.services.detailed_report import (
    DetailedReportService,
    ReportNotFoundError,
)
from app.core.services.payment import PaymentService
from app.core.services.user_bot_profile import UserBotProfileService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    '/{user_id}/bots/{bot_id}/reports/latest-detailed',
    response_model=NextActionSchema,
    responses={status.HTTP_404_NOT_FOUND: {'model': ReportNotFound}},
    summary='Get latest detailed weekly report',
    description=(
        'Retrieves the latest weekly report for a user and bot. '
        'If the detailed report has not been generated yet, '
        'it will be generated on-demand.'
    ),
)
async def get_latest_detailed_report(
    report_service: Annotated[
        DetailedReportService, Depends(get_detailed_report_service)
    ],
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    bot_id_str: Annotated[
        str,
        Path(alias='bot_id', description='Bot ID (e.g., Bulgarian, English)'),
    ],
) -> NextActionSchema:
    try:
        bot_id = BotID(bot_id_str)

        user_profile = await user_bot_profile_service.get(user_id, bot_id)
        if not user_profile:
            raise ReportNotFoundError(
                f'User profile not found for user {user_id} '
                f'and bot {bot_id_str}'
            )

        report = await report_service.generate_detailed_report(user_profile)

        if not report.full_report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Failed to generate full report content.',
            )

        donation_details = payment_service.get_weekly_report_donation_details(
            user_language=user_profile.user_language
        )

        return NextActionSchema(
            action=UserAction.SHOW_MESSAGE_WITH_DONATION,
            message=report.full_report,
            payment_info=donation_details,
        )
    except ReportNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bot_id: '{bot_id_str}'",
        ) from e
