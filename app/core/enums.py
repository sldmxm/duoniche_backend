import logging
import random
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExerciseType(Enum):
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    CHOOSE_SENTENCE = 'choose_sentence'
    CHOOSE_ACCENT = 'choose_accent'
    STORY_COMPREHENSION = 'story_comprehension'

    @classmethod
    def get_next_type(
        cls, distribution: Optional[Dict['ExerciseType', float]] = None
    ) -> 'ExerciseType':
        """
        Selects the next exercise type based on the provided distribution.
        If distribution is None, empty, or invalid,
        falls back to default weights.
        """
        if distribution:
            population = []
            weights = []
            for ex_type, weight in distribution.items():
                if isinstance(ex_type, cls):
                    population.append(ex_type)
                    weights.append(weight)
                else:
                    logger.warning(
                        f'Invalid key type in exercise type distribution: '
                        f'{type(ex_type).__name__}. Expected {cls.__name__}.'
                    )

            if population and sum(weights) > 0:
                try:
                    return random.choices(
                        population=population, weights=weights
                    )[0]
                except ValueError as e:
                    logger.error(
                        f'ValueError in random.choices with provided '
                        f'distribution: {distribution}. Error: {e}'
                    )
                    pass
            elif population:
                logger.warning(
                    f'Provided exercise type distribution has non-positive '
                    f'weights or sums to zero: {distribution}. '
                    f'Falling back to default.'
                )
                pass
            else:
                logger.warning(
                    f'Provided exercise type distribution is empty or '
                    f'contains no valid keys: {distribution}. '
                    f'Falling back to default.'
                )
                pass

        types: List[ExerciseType] = list(ExerciseType)
        default_weights = [
            0.40,  # FILL_IN_THE_BLANK
            0.30,  # CHOOSE_SENTENCE
            0.10,  # CHOOSE_ACCENT
            0.20,  # STORY_COMPREHENSION
        ]
        if len(default_weights) != len(types):
            logger.error(
                'Default weights list length does not match '
                'ExerciseType count! Using random choice.'
            )
            return random.choice(types)

        logger.info('Using default exercise type distribution.')
        choice = random.choices(population=types, weights=default_weights)[0]
        return choice


class ExerciseUiTemplates(Enum):
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    CHOOSE = 'choose'
    AUDIO_CHOOSE = 'audio_choose'


class LanguageLevel(Enum):
    A1 = 'A1'
    A2 = 'A2'
    B1 = 'B1'
    B2 = 'B2'
    C1 = 'C1'
    C2 = 'C2'

    @classmethod
    def get_next_exercise_level(
        cls, current_level: 'LanguageLevel'
    ) -> 'LanguageLevel':
        """
        Get new exercise level based on current level:
        75% same, 10% higher + 1, 5% higher + 2, 10% lower -1
        """
        levels: List[LanguageLevel] = list(LanguageLevel)
        idx = levels.index(current_level)
        choice = random.choices(
            population=[0, 1, 2, -1],
            weights=[0.75, 0.10, 0.05, 0.10],
        )[0]
        new_idx = max(0, min(idx + choice, len(levels) - 1))
        return levels[new_idx]


class UserAction(str, Enum):
    new_exercise = 'new_exercise'
    praise_and_next_set = 'praise_and_next_set'
    congratulations_and_wait = 'congratulations_and_wait'
    limit_reached = 'limit_reached'
    error = 'error'


class ExerciseStatus(str, Enum):
    PUBLISHED = 'published'
    PENDING_REVIEW = 'pending_review'
    REJECTED_BY_ASSESSOR = 'rejected_by_assessor'
    REJECTED_BY_ERROR = 'rejected_by_error'
    ARCHIVED = 'archived'
    AUDIO_GENERATION_ERROR = 'audio_generation_error'
    PROCESSING_ERROR_RETRY = 'processing_error_retry'
    PENDING_ADMIN_REVIEW = 'pending_admin_review'


class UserStatus(str, Enum):
    FREE = 'free'
    TRIAL = 'trial'
    PREMIUM = 'premium'
    CUSTOM = 'custom'
