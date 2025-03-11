import json
from typing import List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.interfaces.llm_provider import LLMProvider
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData


class FillInTheBlankExerciseDataParsed(BaseModel):
    """Class for Fill In The Blank Exercise"""

    text_with_blanks: str = Field(
        description='Sentence with one or more words missing (blanks). '
        'Use "___" for blanks.'
    )
    options: List[str] = Field(
        description='A list of words including the correct '
        'word and some incorrect words to fill the blank.'
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
            openai_api_key=openai_api_key,
            model_name=model_name,
            temperature=settings.openai_temperature,
            max_retries=settings.openai_max_retries,
            request_timeout=settings.openai_request_timeout,
        )

    async def generate_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise:
        """Generate exercise for user."""
        if exercise_type == ExerciseType.FILL_IN_THE_BLANK.value:
            return await self._generate_fill_in_the_blank_exercise(
                user, language_level
            )
        else:
            raise NotImplementedError

    async def _generate_fill_in_the_blank_exercise(
        self, user: User, language_level: str
    ) -> Exercise:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    """You are a language learning assistant.
Generate the exercise for user.
User language: {user_language}
Target language: {target_language}
Language level: {language_level}
Topic: {topic}
""",
                ),
                (
                    'human',
                    'Generate the Fill in the Blank exercise in json format.',
                ),
            ]
        )
        chain = prompt | self.model
        response = await chain.ainvoke(
            {
                'user_language': user.user_language,
                'target_language': user.target_language,
                'language_level': language_level,
                'topic': 'general',  # TODO: Add topic
            }
        )
        try:
            parsed_data = FillInTheBlankExerciseDataParsed.model_validate_json(
                response.content
            )
        except ValidationError as e:
            raise ValueError(
                'Incorrect response from LLM to generate exercise'
            ) from e
        return Exercise(
            exercise_id=0,
            exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
            language_level=language_level,
            topic='general',
            # TODO: вынести тексты заданий в константы
            #  в зависимости от языка пользователя
            exercise_text='Заполни пробелы в предложении',
            data=FillInTheBlankExerciseData(
                text_with_blanks=parsed_data.text_with_blanks,
                words=parsed_data.options,
            ),
        )

    async def validate_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> Tuple[bool, str]:
        if not isinstance(answer, FillInTheBlankAnswer):
            raise NotImplementedError
        if not isinstance(exercise.data, FillInTheBlankExerciseData):
            raise NotImplementedError
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    """You are a language learning assistant.
You need to check the user's answer to the exercise.
User language: {user_language}
Target language: {target_language}
Exercise language level: {language_level}
Exercise topic: {topic}
Options: {options}
Exercise with blanks: {text_with_blanks}
User answer: {user_answer}
Give an answer in the form of json:
{{
"is_correct": bool,
"feedback": str,
}}
""",
                ),
            ]
        )
        chain = prompt | self.model
        try:
            response = await chain.ainvoke(
                {
                    'user_language': user.user_language,
                    'target_language': user.target_language,
                    'language_level': exercise.language_level,
                    'topic': exercise.topic,
                    'text_with_blanks': exercise.data.text_with_blanks,
                    'options': exercise.data.words,
                    'user_answer': exercise.data.get_full_exercise_text(
                        answer
                    ),
                }
            )
        except Exception as e:
            return False, str(e)

        try:
            parsed_response = json.loads(response.content)
            is_correct = parsed_response['is_correct']
            feedback = parsed_response['feedback']

            return is_correct, feedback
        except (json.JSONDecodeError, KeyError) as e:
            return False, f'Invalid LLM Response Format: {e}'
