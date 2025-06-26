from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from app.core.configs.enums import ExerciseType, LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.generation.persona import Persona
from app.core.configs.texts import get_text
from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import StoryComprehensionAnswer
from app.core.value_objects.exercise import StoryComprehensionExerciseData
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.generators.prompt_templates import (
    STORY_COMPREHENSION_GENERATION_INSTRUCTIONS,
    STORY_COMPREHENSION_WITH_PERSONA_GENERATION_INSTRUCTIONS,
)
from app.llm.interfaces.exercise_generator import BaseExerciseGenerator
from app.llm.llm_base import BaseLLMService


class StoryComprehensionLLMOutput(BaseModel):
    story_text: str = Field(description='The short story.')
    correct_statement: str = Field(
        description='The statement that accurately reflects '
        'information from the story.'
    )
    incorrect_statements: List[str] = Field(
        description='A list of two plausible but clearly '
        'false statements about the story.'
    )
    grammar_tags: dict = Field(
        description="A JSON object with keys 'grammar' and 'vocabulary' "
        'listing the topics covered in the story.'
    )


class StoryComprehensionGenerator(BaseExerciseGenerator):
    def __init__(
        self,
        llm_service: BaseLLMService,
    ):
        super().__init__(llm_service)

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, StoryComprehensionAnswer, ExerciseForAssessor]:
        specific_instructions_template = (
            STORY_COMPREHENSION_GENERATION_INSTRUCTIONS
        )

        if persona:
            specific_instructions_template = (
                STORY_COMPREHENSION_WITH_PERSONA_GENERATION_INSTRUCTIONS
            )

        llm_output: StoryComprehensionLLMOutput = (
            await self._run_llm_generation_chain(
                pydantic_output_model=StoryComprehensionLLMOutput,
                specific_instructions=specific_instructions_template,
                user_language_code=user_language,
                target_language=target_language,
                language_level=language_level,
                topic=topic,
                persona=persona,
                user_prompt_text=(
                    "Please generate the 'Story Comprehension' exercise now, "
                    'following all system instructions.'
                ),
            )
        )

        options = [
            llm_output.correct_statement
        ] + llm_output.incorrect_statements

        exercise = Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.STORY_COMPREHENSION,
            exercise_language=target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=get_text(
                ExerciseType.STORY_COMPREHENSION, user_language_code
            ),
            grammar_tags=llm_output.grammar_tags,
            data=StoryComprehensionExerciseData(
                audio_url='',
                audio_telegram_file_id='',
                content_text=llm_output.story_text,
                options=options,
            ),
        )

        correct_answer_obj = StoryComprehensionAnswer(
            answer=llm_output.correct_statement
        )

        exercise_for_quality_assessor = ExerciseForAssessor(
            text=f'Story:\n{llm_output.story_text}\n\n'
            f'Task: {exercise.exercise_text}',
            options=options,
            correct_answer=llm_output.correct_statement,
            correct_options=[llm_output.correct_statement],
            incorrect_options=llm_output.incorrect_statements,
            exercise_type=ExerciseType.STORY_COMPREHENSION,
            language_level=language_level,
        )

        return exercise, correct_answer_obj, exercise_for_quality_assessor
