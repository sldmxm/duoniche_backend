from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.value_objects.answer import Answer, ChooseSentenceAnswer
from app.core.value_objects.exercise import ChooseSentenceExerciseData
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
        "Warning! Feedback for the user must be in user's language."
    )


class ChooseSentenceValidator(ExerciseValidator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def validate(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        """Validate user's answer to the choose-the-sentence exercise."""
        if not isinstance(answer, ChooseSentenceAnswer):
            raise NotImplementedError(
                'Only ChooseSentenceAnswer is implemented'
            )

        if not isinstance(exercise.data, ChooseSentenceExerciseData):
            raise NotImplementedError(
                'Only ChooseSentenceExerciseData is implemented'
            )

        parser = PydanticOutputParser(
            pydantic_object=AttemptValidationResponse
        )

        prompt_template = (
            'You are helping {user_language}-speaking learner '
            'of {exercise_language} language.\n'
            'You need to check if the user has selected '
            'the correct {exercise_language}-sentence from the list.\n'
            'Options: {options}\n'
            'User answer: {user_answer}\n'
            'If answer is incorrect, feedback must be '
            'in {user_language} language.\n'
            '{format_instructions}'
        )

        chain = await self.llm_service.create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        request_data = {
            'user_language': user.user_language,
            'exercise_language': user.target_language,
            'topic': exercise.topic.value,
            'options': exercise.data.sentences,
            'user_answer': exercise.data.get_answered_by_user_exercise_text(
                answer
            ),
        }

        validation_result = await self.llm_service.run_llm_chain(
            chain,
            request_data,
            user,
            exercise.exercise_type,
            exercise.language_level,
        )

        return validation_result.is_correct, validation_result.feedback
