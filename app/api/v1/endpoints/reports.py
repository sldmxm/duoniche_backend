import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import (
    get_language_config_service,
    get_user_bot_profile_service,
    get_user_report_service,
)
from app.api.schemas.report import DetailedReportResponse, ReportNotFoundDetail
from app.core.services.language_config import LanguageConfigService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_report import (
    ReportNotFoundError,
    UserReportService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    '/{user_id}/bots/{bot_id}/reports/latest-detailed',
    response_model=DetailedReportResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {'model': ReportNotFoundDetail},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            'description': 'Invalid bot_id'
        },
    },
    summary='Get or request latest detailed weekly report',
    description=(
        'Retrieves the status of the latest detailed weekly report for '
        'a user and bot. '
        'If it is being generated, a status message is returned. '
        'If it needs to be generated, a task is enqueued '
        'and a status message is returned.'
    ),
)
async def get_latest_detailed_report(
    report_service: Annotated[
        UserReportService, Depends(get_user_report_service)
    ],
    language_config_service: Annotated[
        LanguageConfigService, Depends(get_language_config_service)
    ],
    user_bot_profile_service: Annotated[
        UserBotProfileService, Depends(get_user_bot_profile_service)
    ],
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    bot_id_str: Annotated[
        str,
        Path(alias='bot_id', description='Bot ID (e.g., Bulgarian, English)'),
    ],
) -> DetailedReportResponse:
    bot_id = bot_id_str
    if bot_id not in language_config_service.get_all_bot_ids():
        logger.warning(f'Invalid bot_id provided: {bot_id_str}')
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bot_id: '{bot_id_str}'. "
            f'Valid values are: {language_config_service.get_all_bot_ids()}',
        )

    try:
        user_profile = await user_bot_profile_service.get(user_id, bot_id)
        if not user_profile:
            logger.warning(
                f'User profile not found '
                f'for user {user_id} and bot {bot_id_str}'
            )
            raise ReportNotFoundError(
                f'User profile not found '
                f'for user {user_id} and bot {bot_id_str}'
            )

        current_report_status = await report_service.request_detailed_report(
            user_profile
        )

        return DetailedReportResponse(
            current_report_status=current_report_status,
        )

    except ReportNotFoundError as e:
        logger.warning(
            f'Report not found for user {user_id}, bot {bot_id_str}: {e}'
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e
    # General exception catch for unexpected errors
    except Exception as e:
        logger.error(
            f'Unexpected error in get_latest_detailed_report '
            f'for user {user_id}, bot {bot_id_str}: {e}',
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='An unexpected error occurred while '
            'processing your request.',
        ) from e
