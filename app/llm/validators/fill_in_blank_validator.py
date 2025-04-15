from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService


class AttemptValidationResponse(BaseModel):
    is_correct: bool = Field(description='Whether the answer is correct')
    feedback: str = Field(
        description='If answer is correct, empty string. '
        'Else answer the question "What\'s wrong with this user answer?" '
        '- clearly shortly explain grammatical, spelling, '
        'syntactic, semantic or other errors.\n '
        'Explain to the user exactly what he did wrong, never '
        'using the argument "because that\'s how you should have answered"'
        'Warning! Don\'t write "Wrong answer", "Try again" '
        'or other phrases that provide '
        'no practical benefit to the user.'
        "Warning! Feedback for the user in USER'S language."
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
            raise NotImplementedError(
                'Only FillInTheBlankAnswer is implemented'
            )

        if not isinstance(exercise.data, FillInTheBlankExerciseData):
            raise NotImplementedError(
                'Only FillInTheBlankExerciseData is implemented'
            )

        parser = PydanticOutputParser(
            pydantic_object=AttemptValidationResponse
        )

        prompt_template = (
            'You are a language learning assistant.\n'
            "You need to check the user's answer to the exercise.\n"
            'User language: {user_language}\n'
            'Exercise language: {exercise_language}\n'
            'Exercise topic: {topic}\n'
            'Exercise task: {task}\n'
            'Options: {options}\n'
            'Exercise: {exercise}\n'
            'User answer: {user_answer}\n'
            'You have to give feedback in {user_language}.\n'
            '{format_instructions}'
        )

        chain = await self.llm_service.create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        request_data = {
            'user_language': user_language,
            'exercise_language': target_language,
            'topic': exercise.topic.value,
            'task': exercise.exercise_text,
            'exercise': exercise.data.text_with_blanks,
            'options': exercise.data.words,
            'user_answer': exercise.data.get_answered_by_user_exercise_text(
                answer
            ),
        }

        validation_result = await self.llm_service.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return validation_result.is_correct, validation_result.feedback
