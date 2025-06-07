import random
from enum import Enum
from typing import Dict, List, Optional


class ExerciseType(Enum):
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    CHOOSE_SENTENCE = 'choose_sentence'
    CHOOSE_ACCENT = 'choose_accent'
    STORY_COMPREHENSION = 'story_comprehension'

    @classmethod
    def get_next_type(
        cls, distribution: Optional[Dict['ExerciseType', float]] = None
    ) -> 'ExerciseType':
        types: List[ExerciseType] = list(ExerciseType)
        if distribution:
            population = []
            weights = []
            for ex_type in types:
                if ex_type.value in distribution:
                    population.append(ex_type)
                    weights.append(distribution[ex_type])
            if population and any(w > 0 for w in weights):
                return random.choices(population=population, weights=weights)[
                    0
                ]

        default_weights = [
            0.40,
            0.30,
            0.10,
            0.20,
        ]
        choice = random.choices(
            population=range(len(types)), weights=default_weights
        )[0]
        return types[choice]


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
