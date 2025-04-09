# app/llm/factories.py
from app.core.enums import ExerciseType
from app.llm.generators.fill_in_blank_generator import FillInTheBlankGenerator
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService
from app.llm.validators.fill_in_blank_validator import FillInTheBlankValidator


class ExerciseGeneratorFactory:
    @staticmethod
    def create_generator(
        exercise_type: ExerciseType, llm_service: BaseLLMService
    ) -> ExerciseGenerator:
        """Create an appropriate exercise generator based on exercise type."""
        generators = {
            ExerciseType.FILL_IN_THE_BLANK: FillInTheBlankGenerator,
            # Add new exercise types here
        }

        generator_class = generators.get(exercise_type)
        if not generator_class:
            raise NotImplementedError(
                f"Exercise type '{exercise_type}' is not implemented"
            )

        return generator_class(llm_service)


class ExerciseValidatorFactory:
    @staticmethod
    def create_validator(
        exercise_type: ExerciseType, llm_service: BaseLLMService
    ) -> ExerciseValidator:
        """Create an appropriate exercise validator based on exercise type."""
        validators = {
            ExerciseType.FILL_IN_THE_BLANK: FillInTheBlankValidator,
            # Add new exercise types here
        }

        validator_class = validators.get(exercise_type)
        if not validator_class:
            raise NotImplementedError(
                f"Validator for exercise type '{exercise_type}' "
                f'is not implemented'
            )

        return validator_class(llm_service)
