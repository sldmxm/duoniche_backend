import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.api.dependencies import get_detailed_report_service
from app.api.schemas.report import ReportNotFound, UserReportResponse
from app.core.entities.user_bot_profile import BotID
from app.core.services.detailed_report import (
    DetailedReportService,
    ReportNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    '/{user_id}/bots/{bot_id}/reports/latest-detailed',
    response_model=UserReportResponse,
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
    user_id: Annotated[int, Path(description='User ID', ge=1)],
    bot_id_str: Annotated[
        str,
        Path(alias='bot_id', description='Bot ID (e.g., Bulgarian, English)'),
    ],
) -> UserReportResponse:
    try:
        bot_id = BotID(bot_id_str)
        report = await report_service.generate_detailed_report(user_id, bot_id)
        return UserReportResponse.model_validate(report)
    except ReportNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid bot_id: '{bot_id_str}'",
        ) from e
