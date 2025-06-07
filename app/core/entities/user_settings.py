from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.core.entities.user_bot_profile import BotID
from app.core.enums import ExerciseType
from app.core.generation.config import ExerciseTopic


class UserSettings(BaseModel):
    """
    Represents the resolved, effective settings for a user.
    This object is the single source of truth for services
    that need to check user limits and parameters.
    """

    session_exercise_limit: int = Field(
        default=settings.exercises_in_set * settings.sets_in_session,
        description='Total number of exercises a user can do in a session.',
    )
    min_session_interval_minutes: int = Field(
        default=int(settings.delta_between_sessions.total_seconds() / 60),
        description='Minimum time in minutes a user must '
        'wait between sessions.',
    )
    exercises_in_set: int = Field(
        default=settings.exercises_in_set,
        description='Number of exercises in one set before a praise message.',
    )
    exercise_type_distribution: Optional[Dict[ExerciseType, float]] = Field(
        default=None,
        description='Weights for choosing the next exercise type. '
        'If None, default logic is used.',
    )
    exclude_topics: Optional[List[ExerciseTopic]] = Field(
        default=None,
        description='List of allowed topics. '
        'If None, all topics are allowed.',
    )
    allowed_languages: Optional[List[BotID]] = Field(
        default=None,
        description='List of allowed languages. '
        'If None, all languages are allowed.',
    )
