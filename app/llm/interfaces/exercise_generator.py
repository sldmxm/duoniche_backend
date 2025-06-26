from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Type, TypeVar

import httpx
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from app.core.configs.enums import LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.generation.persona import Persona
from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.generators.prompt_templates import (
    BASE_SYSTEM_PROMPT_FOR_GENERATION,
)
from app.llm.llm_base import BaseLLMService
from app.utils.language_code_converter import (
    convert_iso639_language_code_to_full_name,
)

LLMOutputModel = TypeVar('LLMOutputModel', bound=BaseModel)


class BaseExerciseGenerator(ABC):
    def __init__(
        self,
        llm_service: BaseLLMService,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.llm_service = llm_service
        self.http_client = http_client

    def _format_persona_instructions(self, persona: Optional[Persona]) -> str:
        if not persona:
            return ''
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
        return ' '.join(parts)

    def _get_system_prompt_template(
        self,
        specific_instructions: str,
        target_language: str,
    ) -> str:
        system_prompt_template = BASE_SYSTEM_PROMPT_FOR_GENERATION.replace(
            '{specific_exercise_generation_instructions}',
            specific_instructions,
        )
        if target_language == 'Serbian':
            system_prompt_template += (
                '\n\nIMPORTANT: Generate the exercise using the '
                'Latin alphabet for Serbian. Do not use the Cyrillic alphabet.'
            )
        return system_prompt_template

    async def _run_llm_generation_chain(
        self,
        pydantic_output_model: Type[LLMOutputModel],
        specific_instructions: str,
        user_language_code: str,  # ISO code
        target_language: str,  # full
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
        user_prompt_text: str = (
            'Please generate the exercise now, '
            'following all system instructions.'
        ),
        additional_request_data: Optional[Dict[str, Any]] = None,
        system_prompt_override: Optional[str] = None,
        user_prompt_override: Optional[str] = None,
    ) -> LLMOutputModel:
        parser = PydanticOutputParser(pydantic_object=pydantic_output_model)

        final_system_prompt_template = (
            system_prompt_override
            or self._get_system_prompt_template(
                specific_instructions=specific_instructions,
                target_language=target_language,
            )
        )
        final_user_prompt_text = user_prompt_override or user_prompt_text

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', final_system_prompt_template),
                ('user', final_user_prompt_text),
            ]
        )

        chain = await self.llm_service.create_llm_chain(
            chat_prompt, parser, is_chat_prompt=True
        )

        persona_instructions = self._format_persona_instructions(persona)
        user_language_for_prompt = convert_iso639_language_code_to_full_name(
            user_language_code
        )

        request_data = {
            'user_language': user_language_for_prompt,
            'exercise_language': target_language,
            'language_level': language_level.value,
            'topic': topic.value,
            'persona_instructions': persona_instructions,
            'format_instructions': parser.get_format_instructions(),
        }
        if additional_request_data:
            request_data.update(additional_request_data)

        llm_output = await self.llm_service.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )
        return llm_output

    @abstractmethod
    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, Answer, ExerciseForAssessor]:
        pass
