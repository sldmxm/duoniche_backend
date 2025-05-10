from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService
from app.llm.validators.prompt_templates import (
    BASE_SYSTEM_PROMPT_FOR_VALIDATION,
    FILL_IN_THE_BLANK_INSTRUCTIONS,
)


class AttemptValidationResponse(BaseModel):
    is_correct: bool = Field(description='Whether the answer is correct')
    feedback: str = Field(
        description='If answer is correct, empty string. '
        'Else answer the question "What\'s wrong with this user answer?" '
        '- clearly shortly explain grammatical, spelling, '
        'syntactic, semantic or other errors.\n '
        "Warning! Feedback for the user must be in user's language.\n"
        'Be concise.'
    )


class FillInTheBlankValidator(ExerciseValidator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def validate(
        self,
        user_language,
        target_language,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        """Validate user's answer to the fill-in-the-blank exercise."""
        if not isinstance(answer, FillInTheBlankAnswer):
            raise TypeError(
                f'Expected FillInTheBlankAnswer, got {type(answer).__name__}'
            )

        if not isinstance(exercise.data, FillInTheBlankExerciseData):
            raise TypeError(
                f'Expected FillInTheBlankExerciseData for exercise, '
                f'got {type(exercise.data).__name__}'
            )

        parser = PydanticOutputParser(
            pydantic_object=AttemptValidationResponse
        )

        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_VALIDATION.replace(
            '{specific_exercise_instructions}', FILL_IN_THE_BLANK_INSTRUCTIONS
        )

        user_prompt_template = (
            'Please evaluate the following:\n'
            "User's target language to learn: {exercise_language}\n"
            "User's native language (for feedback): {user_language}\n"
            'Exercise topic: {topic}\n'
            'Exercise task description: {task}\n'
            'Full exercise sentence with blanks: {exercise_sentence}\n'
            'Options provided for blanks (if any): {options}\n'
            "User's completed sentence: {user_answer}"
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt_template),
                ('user', user_prompt_template),
            ]
        )

        chain = await self.llm_service.create_llm_chain(
            chat_prompt, parser, is_chat_prompt=True
        )

        request_data = {
            'user_language': user_language,
            'exercise_language': target_language,
            'topic': exercise.topic.value,
            'task': exercise.exercise_text,
            'exercise_sentence': exercise.data.text_with_blanks,
            'options': ', '.join(exercise.data.words)
            if exercise.data.words
            else 'N/A',
            'user_answer': exercise.data.get_answered_by_user_exercise_text(
                answer
            ),
            'format_instructions': parser.get_format_instructions(),
        }

        validation_result = await self.llm_service.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return validation_result.is_correct, validation_result.feedback
