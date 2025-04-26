from typing import Tuple

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.texts import get_text
from app.core.value_objects.answer import ChooseSentenceAnswer
from app.core.value_objects.exercise import ChooseSentenceExerciseData
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.llm_base import BaseLLMService
from app.llm.quality_assessor import ExerciseForAssessor


class ChooseSentenceExerciseDataParsed(BaseModel):
    correct_sentence: str = Field(description='Correct sentence.\n')
    incorrect_sentences: list[str] = Field(
        description=(
            'A list of 2 very similar unique misspelled sentences '
            'that contains a typical mistake, '
            'based on one or two of the following categories:\n'
            '- Forgetting or misplacing the definite article '
            'at the end of a noun\n'
            '- Confusing past tenses and perfect aspect\n'
            '- Misusing object or reflexive pronouns (e.g. го, му, си, се)\n'
            '- Assigning the wrong gender to a noun\n'
            '- Using an incorrect preposition with a verb'
        )
    )


class ChooseSentenceGenerator(ExerciseGenerator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def generate(
        self,
        user_language: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
    ) -> Tuple[Exercise, ChooseSentenceAnswer, ExerciseForAssessor]:
        """Generate a choose-the-sentence exercise."""

        parser = PydanticOutputParser(
            pydantic_object=ChooseSentenceExerciseDataParsed
        )

        prompt_template = (
            'You are helping {user_language}-speaking learner '
            'of {exercise_language} language.\n'
            'Generate the exercise - '
            '1 correct {exercise_language} sentence and '
            '2 very similar misspelled sentences.\n'
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

        sentences = [
            parsed_data.correct_sentence
        ] + parsed_data.incorrect_sentences

        exercise = Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.CHOOSE_SENTENCE,
            exercise_language=target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=get_text(
                ExerciseType.CHOOSE_SENTENCE, user_language
            ),
            data=ChooseSentenceExerciseData(
                options=sentences,
            ),
        )
        correct_answer = ChooseSentenceAnswer(
            answer=parsed_data.correct_sentence
        )

        exercise_for_quality_assessor = ExerciseForAssessor(
            text=exercise.exercise_text,
            options=sentences,
            correct_answer=parsed_data.correct_sentence,
            exercise_type=ExerciseType.CHOOSE_SENTENCE,
            language_level=language_level,
        )

        return exercise, correct_answer, exercise_for_quality_assessor
