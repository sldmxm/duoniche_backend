from typing import Optional, Tuple

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
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
    BASE_SYSTEM_PROMPT_FOR_GENERATION,
    CHOOSE_SENTENCE_GENERATION_INSTRUCTIONS,
)
from app.llm.interfaces.exercise_generator import ExerciseGenerator
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


class ChooseSentenceGenerator(ExerciseGenerator):
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
    ) -> Tuple[Exercise, ChooseSentenceAnswer, ExerciseForAssessor]:
        """Generate a choose-the-sentence exercise."""
        parser = PydanticOutputParser(
            pydantic_object=ChooseSentenceExerciseLLMOutput
        )

        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_GENERATION.replace(
            '{specific_exercise_generation_instructions}',
            CHOOSE_SENTENCE_GENERATION_INSTRUCTIONS,
        )

        user_prompt_template = (
            "Please generate the 'choose the correct sentence' exercise now, "
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

        llm_output: ChooseSentenceExerciseLLMOutput = (
            await self.llm_service.run_llm_chain(
                chain=chain,
                input_data=request_data,
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
