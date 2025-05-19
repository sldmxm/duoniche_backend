import logging

logger = logging.getLogger(__name__)


def is_user_in_canary_group(user_id: int, feature_percentage: int) -> bool:
    """
    Determines if a user is in the canary group based on
    their ID and a percentage.
    """
    if not (0 <= feature_percentage <= 100):
        logger.warning(
            f'Invalid feature_percentage: {feature_percentage}. '
            f'Defaulting to 0% (feature disabled).'
        )
        return False
    if feature_percentage == 100:
        return True
    if feature_percentage == 0:
        return False

    return user_id % 100 < feature_percentage
