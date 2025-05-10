import logging

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.config import settings
from app.core.interfaces.translate_provider import TranslateProvider
from app.llm.llm_base import BaseLLMService
from app.utils.language_code_converter import (
    convert_iso639_language_code_to_full_name,
)

logger = logging.getLogger(__name__)


class LLMTranslateResult(BaseModel):
    translated_text: str = Field(
        ...,
        description='Translated to the target language text.',
    )
    source_language: str = Field(
        ...,
        description='ISO 639-1 code input text Language: '
        '"en" - English, "bg" - Bulgarian, '
        '"ru" - Russian, "uk" - Ukrainian, etc.',
    )


class LLMTranslator(BaseLLMService, TranslateProvider):
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_translator_model_name,
    ):
        if not model_name:
            raise ValueError(
                'OPENAI_TRANSLATOR_MODEL_NAME environment variable is not set'
            )
        super().__init__(
            openai_api_key=openai_api_key,
            model_name=model_name,
        )

    async def translate_feedback(
        self,
        feedback: str,
        user_language: str,
        exercise_data: str,
        user_answer: str,
        exercise_language: str,
    ) -> str:
        parser = PydanticOutputParser(pydantic_object=LLMTranslateResult)

        user_language_for_prompt = convert_iso639_language_code_to_full_name(
            user_language
        )

        prompt_template = (
            'You are an experienced {exercise_language} language teacher. '
            'Your task is to translate for '
            'a {user_language}-speaking learner '
            'a teacher’s comment on an answer, '
            'preserving its pedagogical meaning, tone, and structure.'
            'Instructions: \n'
            '- First, identify the language of the original comment.\n'
            '- Provide an accurate and natural translation '
            'of the comment into {user_language}, '
            'keeping the explanatory style.\n'
            '- Any words or phrases in quotation marks (e.g., "изпих го") '
            'are excerpts from the original exercise or student answers '
            '— do not change or translate them.\n'
            '- Do not add any new information.\n'
            '- The translated comment must be clear and understandable '
            'for a student who only speaks {user_language}.\n'
            'Exercise data: {exercise_data}\n'
            "Student's answer: {user_answer}\n"
            'Original comment:{feedback}\n'
            '{format_instructions}'
        )

        chain = await self.create_llm_chain(
            prompt_template, parser, is_chat_prompt=False
        )

        request_data = {
            'user_language': user_language_for_prompt,
            'feedback': feedback,
            'exercise_data': exercise_data,
            'user_answer': user_answer,
            'exercise_language': exercise_language,
        }

        result = await self.run_llm_chain(
            chain=chain,
            input_data=request_data,
        )

        return result.translated_text

    async def translate_text(self, text: str, target_language: str) -> str:
        raise NotImplementedError
