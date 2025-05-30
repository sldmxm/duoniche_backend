import logging

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import settings
from app.core.enums import ExerciseType, LanguageLevel
from app.llm.assessors.prompts import SYSTEM_PROMPT_TEMPLATE
from app.llm.llm_base import BaseLLMService
from app.metrics import BACKEND_LLM_METRICS

logger = logging.getLogger(__name__)


class RejectedByAssessor(Exception): ...


class ExerciseForAssessor(BaseModel):
    text: str
    options: list[str]
    correct_answer: str
    exercise_type: ExerciseType
    language_level: LanguageLevel


class LLMExerciseReview(BaseModel):
    # issues: list[str] = Field(
    #     ...,
    #     description='Empty if is valid. '
    #     'Description of the problems found in English. Be concise.',
    # )
    is_valid: bool = Field(
        ..., description='True if the exercise is correct and useful'
    )


class ExerciseQualityAssessor(BaseLLMService):
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_assessor_model_name,
    ):
        if not model_name:
            raise ValueError(
                'OPENAI_ASSESSOR_MODEL_NAME environment variable is not set'
            )
        super().__init__(
            openai_api_key=openai_api_key,
            model_name=model_name,
        )

    async def assess(
        self, exercise: ExerciseForAssessor, user_language, target_language
    ) -> None:
        if self._has_duplicate_options(exercise):
            BACKEND_LLM_METRICS['exercises_rejected'].labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
                user_language=user_language,
                target_language=target_language,
                llm_model=self.model.model_name,
            ).inc()
            message = (
                f'Exercise rejected: duplicate options in answers. '
                f'Exercise: {exercise}'
            )
            raise RejectedByAssessor(message)

        if exercise.exercise_type in (
            ExerciseType.FILL_IN_THE_BLANK,
        ) and self._has_too_long_options(exercise):
            BACKEND_LLM_METRICS['exercises_rejected'].labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
                user_language=user_language,
                target_language=target_language,
                llm_model=self.model.model_name,
            ).inc()
            message = (
                f'Exercise rejected: too long options. '
                f'Exercise: {exercise}'
            )
            raise RejectedByAssessor(message)

        review = await self._run_llm_check(
            exercise, user_language, target_language
        )
        if not review.is_valid:
            BACKEND_LLM_METRICS['exercises_rejected'].labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
                user_language=user_language,
                target_language=target_language,
                llm_model=self.model.model_name,
            ).inc()
            message = (
                f'Exercise rejected by LLM'  # {review.issues}. '
                f'Exercise: {exercise}'
            )
            raise RejectedByAssessor(message)

        logger.info(
            f'Exercise reviewed and accepted by LLM. ' f'Exercise: {exercise}'
        )

    @staticmethod
    def _has_duplicate_options(exercise: ExerciseForAssessor) -> bool:
        return len(set(exercise.options)) < len(exercise.options)

    @staticmethod
    def _has_too_long_options(exercise: ExerciseForAssessor) -> bool:
        TELEGRAM_BUTTON_MAX_LENGTH = 64
        for option in exercise.options:
            if len(option.encode('utf-8')) > TELEGRAM_BUTTON_MAX_LENGTH:
                return True
        return False

    async def _run_llm_check(
        self,
        exercise: ExerciseForAssessor,
        user_language: str,
        target_language: str,
    ) -> LLMExerciseReview:
        parser = PydanticOutputParser(pydantic_object=LLMExerciseReview)

        user_prompt_template = (
            'Please assess the following exercise:\n'
            'Target Language: {target_language}\n'
            "Learner's Native Language: {user_language}\n"
            'Exercise Type: {exercise_type}\n'
            'Language Level: {language_level}\n'
            'Exercise Text/Question: {text}\n'
            'Provided Options: {options_formatted}\n'
            'Designated Correct Answer: {correct_answer}\n\n'
            'Based on the system instructions, provide your assessment.\n'
            '{format_instructions}'
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', SYSTEM_PROMPT_TEMPLATE),
                ('user', user_prompt_template),
            ]
        )
        chain = await self.create_llm_chain(
            chat_prompt, parser, is_chat_prompt=True
        )

        options_formatted_str = (
            ', '.join(f"'{opt}'" for opt in exercise.options)
            if exercise.options
            else 'N/A'
        )

        request_data = {
            'user_language': user_language,
            'target_language': target_language,
            'text': exercise.text,
            'exercise_type': exercise.exercise_type.value,
            'language_level': exercise.language_level.value,
            'options_formatted': options_formatted_str,
            'correct_answer': exercise.correct_answer,
            'format_instructions': parser.get_format_instructions(),
        }

        review: LLMExerciseReview = await self.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return review


class ValidateAttemptQualityAssessor(BaseLLMService):
    # TODO: проверять качество ответа,
    #  если не очень, поднимать исключение, его поймает Core
    ...
