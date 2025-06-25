import re
from typing import Optional, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import settings
from app.core.configs.enums import ExerciseType, LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.generation.persona import Persona
from app.core.configs.texts import get_text
from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.generators.prompt_templates import (
    BASE_SYSTEM_PROMPT_FOR_GENERATION,
    FILL_IN_THE_BLANK_GENERATION_INSTRUCTIONS,
)
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.llm_base import BaseLLMService


class FillInTheBlankExerciseLLMOutput(BaseModel):
    text_with_blanks: str = Field(
        description='Sentence with one or more blanks.\n'
        'If sentence consists more than 11 words, make 2 blanks.\n'
        f'Use "{settings.exercise_fill_in_the_blank_blanks}" for blanks.\n'
    )
    correct_words: list[str] = Field(
        description=(
            'A list of SINGLE words that correctly fill the blanks, in order.'
        )
    )
    incorrect_options: list[str] = Field(
        description=(
            'A list of incorrect SINGLE word options designed as distractors. '
            'These should make the sentence grammatically wrong or '
            'semantically absurd when used in the blanks. '
            'Must use {exercise_language} alphabet only.'
        )
    )
    grammar_tags: dict = Field(
        description="A JSON object with keys 'grammar' and 'vocabulary' "
        'listing the topics covered in the exercise.'
    )


class FillInTheBlankGenerator(ExerciseGenerator):
    def __init__(self, llm_service: BaseLLMService):
        self.llm_service = llm_service

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, FillInTheBlankAnswer, ExerciseForAssessor]:
        """Generate a fill-in-the-blank exercise."""

        parser = PydanticOutputParser(
            pydantic_object=FillInTheBlankExerciseLLMOutput
        )

        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_GENERATION.replace(
            '{specific_exercise_generation_instructions}',
            FILL_IN_THE_BLANK_GENERATION_INSTRUCTIONS,
        )

        user_prompt_template = (
            'Please generate the fill-in-the-blank exercise now, '
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

        persona_instructions = ''
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

        request_data = {
            'user_language': user_language,
            'exercise_language': target_language,
            'language_level': language_level.value,
            'topic': topic.value,
            'persona_instructions': persona_instructions,
            'format_instructions': parser.get_format_instructions(),
        }

        llm_output: FillInTheBlankExerciseLLMOutput = (
            await self.llm_service.run_llm_chain(
                chain=chain,
                input_data=request_data,
            )
        )

        text_with_blanks = re.sub(
            r'_{2,}',
            settings.exercise_fill_in_the_blank_blanks,
            llm_output.text_with_blanks,
        )
        words = llm_output.correct_words + llm_output.incorrect_options

        exercise = Exercise(
            exercise_id=None,
            exercise_type=ExerciseType.FILL_IN_THE_BLANK,
            exercise_language=target_language,
            language_level=language_level,
            topic=topic,
            exercise_text=get_text(
                ExerciseType.FILL_IN_THE_BLANK, user_language_code
            ),
            grammar_tags=llm_output.grammar_tags,
            data=FillInTheBlankExerciseData(
                text_with_blanks=text_with_blanks,
                words=words,
            ),
        )
        correct_answer = FillInTheBlankAnswer(words=llm_output.correct_words)

        exercise_for_quality_assessor = ExerciseForAssessor(
            text=exercise.exercise_text + '\n' + text_with_blanks,
            options=words,
            correct_answer=exercise.data.get_answered_by_user_exercise_text(
                correct_answer
            ),
            correct_options=llm_output.correct_words,
            incorrect_options=llm_output.incorrect_options,
            exercise_type=ExerciseType.FILL_IN_THE_BLANK,
            language_level=language_level,
        )

        return exercise, correct_answer, exercise_for_quality_assessor
