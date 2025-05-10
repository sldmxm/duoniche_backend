from typing import Tuple

from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService


class AttemptValidationResponse(BaseModel):
    is_correct: bool = Field(description='Whether the answer is correct')


class ChooseAccentValidator(ExerciseValidator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def validate(
        self,
        user_language: str,
        target_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        # TODO: LLM не умеют в ударение, сейчас не используется,
        #  но можно попробовать допилить
        raise NotImplementedError
        #
        #
        # if not isinstance(answer, ChooseAccentAnswer):
        #     raise NotImplementedError(
        #         'Only ChooseAccentAnswer is implemented')
        #
        # if not isinstance(exercise.data, ChooseAccentExerciseData):
        #     raise NotImplementedError(
        #         'Only ChooseAccentExerciseData is implemented'
        #     )
        #
        # parser = PydanticOutputParser(
        #     pydantic_object=AttemptValidationResponse
        # )
        #
        # prompt_template = (
        #     'You are helping {user_language}-speaking learner '
        #     'of {exercise_language} language.\n'
        #     'You need to check if the user has selected '
        #     'the correct accent from the list.\n'
        #     'Options: {options}\n'
        #     'User answer: {user_answer}\n'
        #     '{format_instructions}'
        # )
        #
        # chain = await self.llm_service.create_llm_chain(
        #     prompt_template, parser, is_chat_prompt=False
        # )
        #
        # request_data = {
        #     'user_language': user_language,
        #     'exercise_language': target_language,
        #     'topic': exercise.topic.value,
        #     'options': exercise.data.options,
        #     'user_answer': exercise.data.get_answered_by_user_exercise_text(
        #         answer
        #     ),
        # }
        #
        # validation_result = await self.llm_service.run_llm_chain(
        #     chain=chain,
        #     input_data=request_data,
        # )
        #
        # return validation_result.is_correct, ''
