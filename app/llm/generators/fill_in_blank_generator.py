import re
from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.consts import (
    EXERCISE_FILL_IN_THE_BLANK_BLANKS,
)
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.texts import get_text
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.llm_base import BaseLLMService
from app.llm.quality_assessor import ExerciseForAssessor


class FillInTheBlankExerciseDataParsed(BaseModel):
    text_with_blanks: str = Field(
        description='Sentence with one or more blanks.\n'
        'If sentence consists more than 11 words, make 2 blanks.\n'
        f'Use "{EXERCISE_FILL_IN_THE_BLANK_BLANKS}" for blanks.\n'
        "Don't write the words in brackets."
    )
    right_words: list[str] = Field(
        description=(
            'A list of *single* word '
            'or UNIQUE words to correct fill the blanks. '
            'The number of words must be equal to the number of the blanks.'
        )
    )
    wrong_words: list[str] = Field(
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
            'bad wrong_words: '
            '["работать", "путешествовать", "отдыхать", "жить"]\n'
            'good ng_words: '
            '["работать", "работает", "работают", "путешественник"]'
        )
    )


class FillInTheBlankGenerator(ExerciseGenerator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def generate(
        self,
        user_language: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
    ) -> Tuple[Exercise, FillInTheBlankAnswer, ExerciseForAssessor]:
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

        chain = await self.llm_service.create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        input_data = {
            'user_language': user_language,
            'exercise_language': target_language,
            'language_level': language_level.value,
            'topic': topic.value,
        }

        parsed_data = await self.llm_service.run_llm_chain(
            chain=chain,
            input_data=input_data,
        )

        text_with_blanks = re.sub(
            r'_{2,}',
            EXERCISE_FILL_IN_THE_BLANK_BLANKS,
            parsed_data.text_with_blanks,
        )
        words = parsed_data.right_words + parsed_data.wrong_words

        exercise = Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.FILL_IN_THE_BLANK,
            exercise_language=target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=get_text(
                ExerciseType.FILL_IN_THE_BLANK, user_language
            ),
            data=FillInTheBlankExerciseData(
                text_with_blanks=text_with_blanks,
                words=words,
            ),
        )
        correct_answer = FillInTheBlankAnswer(words=parsed_data.right_words)

        exercise_for_quality_assessor = ExerciseForAssessor(
            text=text_with_blanks,
            options=words,
            correct_answer=exercise.data.get_answered_by_user_exercise_text(
                correct_answer
            ),
            exercise_type=ExerciseType.FILL_IN_THE_BLANK,
            language_level=language_level,
        )

        return exercise, correct_answer, exercise_for_quality_assessor
