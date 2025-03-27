import logging
import re
from typing import Any, Dict, List, Tuple, TypeVar, Union

from langchain_core.output_parsers import (
    JsonOutputParser,
    PydanticOutputParser,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.core.consts import (
    EXERCISE_FILL_IN_THE_BLANK_BLANKS,
    EXERCISE_FILL_IN_THE_BLANK_TASK,
)
from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.interfaces.llm_provider import LLMProvider
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FillInTheBlankExerciseDataParsed(BaseModel):
    text_with_blanks: str = Field(
        description='Sentence with one or more blanks.\n'
        'If sentence consists more than 9 words, make 2 blanks.\n'
        f'Use "{EXERCISE_FILL_IN_THE_BLANK_BLANKS}" for blanks.\n'
        "Don't write the words in brackets."
    )
    right_words: List[str] = Field(
        description=(
            'A list of *single* word or words to correct fill the blanks. '
            'The number of words must be equal to the number of the blanks.'
        )
    )
    wrong_words: List[str] = Field(
        description=(
            'A list of 3 single UNIQUE words to incorrectly fill the blanks '
            'with form OR grammatical OR typo errors '
            'OR obviously inappropriate in meaning.\n'
            'Warning! Prioritize incorrect forms of the *CORRECT WORD*, '
            'wrong grammatical cases, or unrelated nonsense words.\n'
            'Warning! Make sure NONE of the words could '
            'logically fit the sentence.\n'
            'Example:\n'
            'text_with_blanks: '
            '"После университета он планирует ___ в другой стране."\n'
            'wrong_words: '
            '["работать", "путешествовать", "отдыхать", "жить"] '
            '- плохой результат.\n'
            'wrong_words: '
            '["работать", "работает", "работают", "путешественник"] '
            '- ожидаемый результат.\n'
        )
    )


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


class LLMService(LLMProvider):
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_model_name,
    ):
        if not openai_api_key:
            raise ValueError('OPENAI_API_KEY environment variable is not set')

        self.model = ChatOpenAI(
            api_key=openai_api_key,
            model=model_name,
            # temperature=settings.openai_temperature,
            # max_retries=settings.openai_max_retries,
            # timeout=settings.openai_request_timeout,
        )

    async def generate_exercise(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
        topic: str = 'general',
    ) -> tuple[Exercise, Answer]:
        """Generate exercise for user based on exercise type."""
        exercise_generators = {
            ExerciseType.FILL_IN_THE_BLANK.value: (
                self._generate_fill_in_the_blank_exercise
            ),
        }

        generator = exercise_generators.get(exercise_type)
        if not generator:
            raise NotImplementedError(
                f"Exercise type '{exercise_type}' is not implemented"
            )

        return await generator(
            user=user, language_level=language_level, topic=topic
        )

    async def _create_llm_chain(
        self,
        prompt_template: str,
        output_parser: Union[PydanticOutputParser, JsonOutputParser],
        is_chat_prompt: bool = False,
    ) -> RunnableSerializable:
        """Create a standardized LLM chain with proper error handling."""
        if is_chat_prompt:
            prompt = ChatPromptTemplate.from_messages(
                [('system', prompt_template)]
            )
        else:
            from langchain_core.prompts import PromptTemplate

            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=[],
                partial_variables={
                    'format_instructions': (
                        output_parser.get_format_instructions()
                    )
                },
            )

        chain = prompt | self.model | output_parser
        return chain

    async def _run_llm_chain(
        self,
        chain: RunnableSerializable,
        input_data: Dict[str, Any],
    ) -> Any:
        """Execute LLM chain with standardized logging and error handling."""
        try:
            logger.debug(f'LLM request data: {input_data}')
            response = await chain.ainvoke(input_data)
            logger.debug(f'LLM response: {response}')
            return response
        except ValidationError as e:
            logger.error(f'Validation error in LLM response: {e}')
            raise ValueError(f'Invalid response format from LLM: {e}') from e
        except GeneratorExit:
            logger.warning('LLM request was interrupted')
            raise
        except Exception as e:
            logger.error(f'Error during LLM request: {e}')
            raise RuntimeError(f'LLM service error: {e}') from e

    async def _generate_fill_in_the_blank_exercise(
        self,
        user: User,
        language_level: str,
        topic: str,
    ) -> tuple[Exercise, Answer]:
        """Generate a fill-in-the-blank exercise."""
        parser = PydanticOutputParser(
            pydantic_object=FillInTheBlankExerciseDataParsed
        )

        prompt_template = (
            'You are a language learning assistant.\n'
            'Generate the exercise - '
            'ONE sentence with one or more words missing.\n'
            'User language: {user_language}\n'
            'Target language: {exercise_language}\n'
            'Language level: {language_level}\n'
            'Topic: {topic}\n'
            '{format_instructions}'
        )

        chain = await self._create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        request_data = {
            'user_language': user.user_language,
            'exercise_language': user.target_language,
            'language_level': language_level,
            'topic': topic,
        }

        parsed_data = await self._run_llm_chain(chain, request_data)

        # TODO: проверить, что в set(правильные+неправильные) > 3
        # TODO: если правильных слов больше чем пропусков,
        #  удалить лишние правильные слова

        text_with_blanks = re.sub(
            r'_{2,}',
            EXERCISE_FILL_IN_THE_BLANK_BLANKS,
            parsed_data.text_with_blanks,
        )

        return Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            exercise_language=user.target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=EXERCISE_FILL_IN_THE_BLANK_TASK,
            data=FillInTheBlankExerciseData(
                text_with_blanks=text_with_blanks,
                words=parsed_data.right_words + parsed_data.wrong_words,
            ),
        ), FillInTheBlankAnswer(words=parsed_data.right_words)

    async def validate_attempt(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
        right_answers: List[Answer],
    ) -> Tuple[bool, str]:
        """Validate user's answer to the exercise."""
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

        chain = await self._create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )
        # TODO: сделать универсальный промпт для любых типов упражнений
        request_data = {
            'user_language': user.user_language,
            'exercise_language': user.target_language,
            'topic': exercise.topic,
            'task': exercise.exercise_text,
            'exercise': exercise.data.text_with_blanks,
            'options': exercise.data.words,
            'user_answer': exercise.data.get_answered_by_user_exercise_text(
                answer
            ),
        }

        validation_result = await self._run_llm_chain(chain, request_data)
        return validation_result.is_correct, validation_result.feedback
