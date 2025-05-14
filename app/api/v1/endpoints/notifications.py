import logging

from fastapi import APIRouter, Query

from app.core.entities.user_bot_profile import BotID

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    '/{task_id}/check_relevance/',
    summary='Check if a notification task is still relevant for a user.',
    response_description='Returns a boolean indicating if '
    'the notification is relevant.',
)
async def check_notification_relevance(
    task_id: str,
    bot_id: BotID = Query(
        ..., description='The ID of the bot (language pair).'
    ),
    user_id: int = Query(..., description='The ID of the user.'),
):
    """
    Checks if a notification task is still relevant to be sent to the user.

    - **task_id**: The unique identifier of the notification task.
    - **bot_id**: The identifier of the bot (e.g., "Bulgarian").
    - **user_id**: The unique identifier of the user.

    On the first stage, this endpoint will always return
    `{"is_relevant": True}`.
    Future enhancements will include logic to check:
    - User's current status in the bot (e.g., active, blocked).
    - User's notification preferences.
    - Specific conditions related to the notification type (e.g.,
    if a session
      reminder is still needed if the user already started a session).
    """
    logger.info(
        f'Checking relevance for notification task_id: {task_id}, '
        f'user_id: {user_id}, bot_id: {bot_id.value}'
    )

    # TODO: Implement actual relevance check logic here.
    # For now, always return True as per the initial requirement.
    is_relevant = True

    if not is_relevant:
        logger.info(
            f'Notification task {task_id} for user {user_id} '
            f'is no longer relevant.'
        )

    return {'is_relevant': is_relevant}
