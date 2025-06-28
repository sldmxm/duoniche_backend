from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.core.configs.enums import ExerciseType
from app.core.configs.generation.config import ExerciseTopic


class UserCustomSettings(BaseModel):
    """
    A partial UserSettings model used for storing user-specific overrides.
    Fields are optional as only a subset might be customized.
    This model handles automatic conversion of string keys/values to Enums.
    """

    session_exercise_limit: Optional[int] = None
    min_session_interval_minutes: Optional[int] = None
    exercises_in_set: Optional[int] = None
    available_exercise_types: Optional[List[ExerciseType]] = None
    exercise_type_distribution: Optional[Dict[ExerciseType, float]] = None
    exclude_topics: Optional[List[ExerciseTopic]] = None
    allowed_languages: Optional[List[str]] = None
    alphabet: Optional[str] = None

    model_config = ConfigDict(extra='forbid')


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
    available_exercise_types: List[ExerciseType] = Field(
        default_factory=list,
        description='List of available exercise types for a user.',
    )
    exercise_type_distribution: Dict[ExerciseType, float] = Field(
        default_factory=dict,
        description='Distribution of exercise types for a user.',
    )
    exclude_topics: Optional[List[ExerciseTopic]] = Field(
        default=None,
        description='List of allowed topics. '
        'If None, all topics are allowed.',
    )
    allowed_languages: Optional[List[str]] = Field(
        default=None,
        description='List of allowed languages. '
        'If None, all languages are allowed.',
    )
