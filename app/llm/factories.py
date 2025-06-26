import httpx

from app.core.configs.enums import ExerciseType
from app.llm.generators.choose_accent_generator import ChooseAccentGenerator
from app.llm.generators.choose_sentence_generator import (
    ChooseSentenceGenerator,
)
from app.llm.generators.fill_in_blank_generator import FillInTheBlankGenerator
from app.llm.generators.story_comprehension_generator import (
    StoryComprehensionGenerator,
)
from app.llm.interfaces.exercise_generator import BaseExerciseGenerator
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService
from app.llm.validators.choose_sentence_validator import (
    ChooseSentenceValidator,
)
from app.llm.validators.fill_in_blank_validator import FillInTheBlankValidator


class ExerciseGeneratorFactory:
    @staticmethod
    def create_generator(
        exercise_type: ExerciseType,
        llm_service: BaseLLMService,
        http_client: httpx.AsyncClient,
    ) -> BaseExerciseGenerator:
        """Create an appropriate exercise generator based on exercise type."""
        generators = {
            ExerciseType.FILL_IN_THE_BLANK: FillInTheBlankGenerator,
            ExerciseType.CHOOSE_SENTENCE: ChooseSentenceGenerator,
            ExerciseType.CHOOSE_ACCENT: ChooseAccentGenerator,
            ExerciseType.STORY_COMPREHENSION: StoryComprehensionGenerator,
        }

        generator_class = generators.get(exercise_type)
        if not generator_class:
            raise NotImplementedError(
                f"Exercise type '{exercise_type}' is not implemented"
            )

        if exercise_type == ExerciseType.CHOOSE_ACCENT:
            return generator_class(
                llm_service=llm_service, http_client=http_client
            )  # type: ignore
        else:
            return generator_class(llm_service=llm_service)  # type: ignore


class ExerciseValidatorFactory:
    @staticmethod
    def create_validator(
        exercise_type: ExerciseType, llm_service: BaseLLMService
    ) -> ExerciseValidator:
        """Create an appropriate exercise validator based on exercise type."""
        validators = {
            ExerciseType.FILL_IN_THE_BLANK: FillInTheBlankValidator,
            ExerciseType.CHOOSE_SENTENCE: ChooseSentenceValidator,
        }

        validator_class = validators.get(exercise_type)
        if not validator_class:
            raise NotImplementedError(
                f"Validator for exercise type '{exercise_type}' "
                f'is not implemented'
            )

        return validator_class(llm_service)  # type: ignore
