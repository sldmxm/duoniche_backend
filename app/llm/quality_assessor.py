import logging

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.config import settings
from app.core.enums import ExerciseType, LanguageLevel
from app.llm.llm_base import BaseLLMService
from app.metrics import BACKEND_LLM_METRICS

logger = logging.getLogger(__name__)


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
        # TODO: Если может исправить, исправлять и присылать новый вариант,
        #  если не может, откидывать
        if self._has_duplicate_options(exercise):
            message = (
                f'Exercise rejected: duplicate options in answers. '
                f'Exercise: {exercise}'
            )
            raise ValueError(message)

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
                # f'Exercise rejected by LLM: {review.issues}. '
                f'Exercise: {exercise}'
            )
            raise ValueError(message)

        logger.info(
            f'Exercise reviewed and accepted by LLM. ' f'Exercise: {exercise}'
        )

    @staticmethod
    def _has_duplicate_options(exercise: ExerciseForAssessor) -> bool:
        return len(set(exercise.options)) < len(exercise.options)

    async def _run_llm_check(
        self, exercise: ExerciseForAssessor, user_language, target_language
    ) -> LLMExerciseReview:
        parser = PydanticOutputParser(pydantic_object=LLMExerciseReview)
        prompt_template = (
            'Analyze the following exercise and answer '
            'for {user_language}-speaking learner '
            'of {target_language} language.\n'
            'Task of the exercise must be in {user_language}.\n'
            '`is_valid` should be true only if the exercise is correct, '
            'educational, free of grammatical or logical errors, '
            'sounds natural and common in {target_language} '
            'and if the incorrect options are truly incorrect.\n\n'
            'Exercise type: {exercise_type}\n'
            'Exercise: {text}\n'
            'Options: {options}\n'
            'Correct answer: {correct_answer}\n'
            '{format_instructions}'
        )

        chain = await self.create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        request_data = {
            'user_language': user_language,
            'target_language': target_language,
            'text': exercise.text,
            'exercise_type': exercise.exercise_type,
            'options': exercise.options,
            'correct_answer': exercise.correct_answer,
        }

        review = await self.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return review


class ValidateAttemptQualityAssessor(BaseLLMService):
    # TODO: проверять качество ответа,
    #  если не очень, менять на вариант ассессора
    ...
