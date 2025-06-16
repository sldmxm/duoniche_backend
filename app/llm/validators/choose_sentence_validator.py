from typing import Dict, List, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer, ChooseSentenceAnswer
from app.core.value_objects.exercise import ChooseSentenceExerciseData
from app.llm.interfaces.exercise_validator import ExerciseValidator
from app.llm.llm_base import BaseLLMService
from app.llm.validators.models import AttemptValidationResponse
from app.llm.validators.prompt_templates import (
    BASE_SYSTEM_PROMPT_FOR_VALIDATION,
    CHOOSE_SENTENCE_INSTRUCTIONS,
)


class ChooseSentenceValidator(ExerciseValidator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def validate(
        self,
        user_language: str,
        target_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str, Dict[str, List[str]]]:
        """Validate user's answer to the choose-the-sentence exercise."""
        if not isinstance(answer, ChooseSentenceAnswer):
            raise TypeError(
                f'Expected ChooseSentenceAnswer, got {type(answer).__name__}',
            )

        if not isinstance(exercise.data, ChooseSentenceExerciseData):
            raise TypeError(
                f'Expected ChooseSentenceExerciseData for exercise, '
                f'got {type(exercise.data).__name__}',
            )

        parser = PydanticOutputParser(
            pydantic_object=AttemptValidationResponse,
        )

        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_VALIDATION.replace(
            '{specific_exercise_instructions}',
            CHOOSE_SENTENCE_INSTRUCTIONS,
        )

        user_prompt_template = (
            "Please evaluate the user's choice:\n"
            "User's target language to learn: {exercise_language}\n"
            "User's native language (for feedback): {user_language}\n"
            'Exercise topic: {topic}\n'
            'Exercise task description: {task}\n'
            'Sentence options provided to the user:\n'
            '{options_formatted}\n'
            "User's chosen sentence: {user_answer_sentence}"
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt_template),
                ('user', user_prompt_template),
            ],
        )

        chain = await self.llm_service.create_llm_chain(
            chat_prompt,
            parser,
            is_chat_prompt=True,
        )

        options_formatted_list = [
            f'- "{opt}"' for opt in exercise.data.options
        ]
        options_formatted_str = '\n'.join(options_formatted_list)

        request_data = {
            'user_language': user_language,
            'exercise_language': target_language,
            'topic': exercise.topic.value,
            'task': exercise.exercise_text,
            'options_formatted': options_formatted_str,
            'user_answer_sentence': answer.answer,
            'format_instructions': parser.get_format_instructions(),
        }

        validation_result = await self.llm_service.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return (
            validation_result.is_correct,
            validation_result.feedback,
            validation_result.error_tags,
        )
