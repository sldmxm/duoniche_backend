from typing import List, Optional, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType, LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.generation.persona import Persona
from app.core.texts import get_text
from app.core.value_objects.answer import StoryComprehensionAnswer
from app.core.value_objects.exercise import StoryComprehensionExerciseData
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.generators.prompt_templates import (
    BASE_SYSTEM_PROMPT_FOR_GENERATION,
    STORY_COMPREHENSION_GENERATION_INSTRUCTIONS,
    STORY_COMPREHENSION_WITH_PERSONA_GENERATION_INSTRUCTIONS,
)
from app.llm.interfaces.exercise_generator import ExerciseGenerator
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


class StoryComprehensionGenerator(ExerciseGenerator):
    def __init__(
        self,
        llm_service: BaseLLMService,
    ):
        self.llm_service = llm_service

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, StoryComprehensionAnswer, ExerciseForAssessor]:
        """Generate a choose-the-sentence exercise."""
        parser = PydanticOutputParser(
            pydantic_object=StoryComprehensionLLMOutput
        )

        persona_instructions = ''
        specific_instructions_template = (
            STORY_COMPREHENSION_GENERATION_INSTRUCTIONS
        )

        if persona:
            parts = [f'Persona: {persona.name}.']
            if persona.role:
                parts.append(f'Role: {persona.role}.')
            if persona.emotion:
                parts.append(f'Emotion: {persona.emotion}.')
            if persona.motivation:
                parts.append(f'Motivation: {persona.motivation}.')
            if persona.communication_style:
                parts.append(
                    f'Communication Style: {persona.communication_style}.'
                )
            persona_instructions = ' '.join(parts)
            specific_instructions_template = (
                STORY_COMPREHENSION_WITH_PERSONA_GENERATION_INSTRUCTIONS
            )

        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_GENERATION.replace(
            '{specific_exercise_generation_instructions}',
            specific_instructions_template,
        )

        user_prompt_template = (
            "Please generate the 'Story Comprehension' exercise now, "
            'following all system instructions.'
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
            'language_level': language_level.value,
            'topic': topic.value,
            'persona_instructions': persona_instructions,
            'format_instructions': parser.get_format_instructions(),
        }

        llm_output: StoryComprehensionLLMOutput = (
            await self.llm_service.run_llm_chain(
                chain=chain,
                input_data=request_data,
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
