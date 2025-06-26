from typing import Optional, Tuple

from pydantic import BaseModel, Field

from app.core.configs.enums import ExerciseType, LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.generation.persona import Persona
from app.core.configs.texts import get_text
from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import ChooseSentenceAnswer
from app.core.value_objects.exercise import ChooseSentenceExerciseData
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.generators.prompt_templates import (
    CHOOSE_SENTENCE_GENERATION_INSTRUCTIONS,
)
from app.llm.interfaces.exercise_generator import BaseExerciseGenerator
from app.llm.llm_base import BaseLLMService


class ChooseSentenceExerciseLLMOutput(BaseModel):
    correct_sentence: str = Field(
        description='The single, grammatically correct sentence.'
    )
    incorrect_sentences: list[str] = Field(
        description='A list of exactly 2 incorrect sentences. '
        'Each should be very similar to the correct one '
        'but contain a clear grammatical error.'
    )
    grammar_tags: dict = Field(
        description="A JSON object with keys 'grammar' and 'vocabulary' "
        'listing the topics covered in the exercise.'
    )


class ChooseSentenceGenerator(BaseExerciseGenerator):
    def __init__(self, llm_service: BaseLLMService):
        super().__init__(llm_service)

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, ChooseSentenceAnswer, ExerciseForAssessor]:
        llm_output: ChooseSentenceExerciseLLMOutput = (
            await self._run_llm_generation_chain(
                pydantic_output_model=ChooseSentenceExerciseLLMOutput,
                specific_instructions=CHOOSE_SENTENCE_GENERATION_INSTRUCTIONS,
                user_language_code=user_language,
                target_language=target_language,
                language_level=language_level,
                topic=topic,
                persona=persona,
                user_prompt_text=(
                    "Please generate the 'choose the correct sentence' "
                    'exercise now, following all system instructions.'
                ),
            )
        )

        options = [
            llm_output.correct_sentence
        ] + llm_output.incorrect_sentences

        exercise = Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.CHOOSE_SENTENCE,
            exercise_language=target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=get_text(
                ExerciseType.CHOOSE_SENTENCE, user_language_code
            ),
            grammar_tags=llm_output.grammar_tags,
            data=ChooseSentenceExerciseData(
                options=options,
            ),
        )

        correct_answer_obj = ChooseSentenceAnswer(
            answer=llm_output.correct_sentence
        )

        exercise_for_quality_assessor = ExerciseForAssessor(
            text=exercise.exercise_text,
            options=options,
            correct_answer=llm_output.correct_sentence,
            correct_options=[llm_output.correct_sentence],
            incorrect_options=llm_output.incorrect_sentences,
            exercise_type=ExerciseType.CHOOSE_SENTENCE,
            language_level=language_level,
        )

        return exercise, correct_answer_obj, exercise_for_quality_assessor
