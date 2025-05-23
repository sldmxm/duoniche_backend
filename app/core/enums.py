import random
from enum import Enum
from typing import List


class ExerciseType(Enum):
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    CHOOSE_SENTENCE = 'choose_sentence'
    CHOOSE_ACCENT = 'choose_accent'
    # SENTENCE_CONSTRUCTION = 'sentence_construction'
    # MULTIPLE_CHOICE = 'multiple_choice'
    # TRANSLATION = 'translation'

    @classmethod
    def get_next_type(cls) -> 'ExerciseType':
        types: List[ExerciseType] = list(ExerciseType)
        choice = random.choices(
            population=[
                0,
                1,
                2,
            ],
            weights=[
                0.60,
                0.30,
                0.10,
            ],
        )[0]
        return types[choice]


class ExerciseUiTemplates(Enum):
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    CHOOSE = 'choose'


class ExerciseTopic(Enum):
    GENERAL = 'general'
    SHOPPING = 'shopping'
    TRAVEL = 'travel'
    FOOD = 'food'
    SPORTS = 'sports'
    WEATHER = 'weather'
    WORK = 'work'
    HEALTH = 'health'
    EMERGENCIES = 'emergencies'
    RELATIONSHIPS = 'relationships'
    TECH = 'tech'
    EDUCATION = 'education'
    ENTERTAINMENT = 'entertainment'
    MONEY = 'money'
    HOME = 'home'
    TRANSPORT = 'transport'
    RESTAURANT = 'restaurant'
    FAMILY = 'family'
    PHARMACY = 'pharmacy'
    NATURE = 'NATURE'
    ANIMALS = 'ANIMALS'
    KIDS = 'KIDS'
    # Add more topics here...

    @classmethod
    def get_next_topic(cls) -> 'ExerciseTopic':
        topics: List[ExerciseTopic] = list(ExerciseTopic)
        return random.choice(topics)


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
