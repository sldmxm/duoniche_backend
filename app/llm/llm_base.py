import logging
from typing import Any, Dict, TypeVar, Union

import tiktoken
from langchain_core.output_parsers import (
    JsonOutputParser,
    PydanticOutputParser,
)
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import settings
from app.core.entities.user import User
from app.core.enums import ExerciseType, LanguageLevel
from app.metrics import BACKEND_LLM_METRICS

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseLLMService:
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_model_name,
    ):
        if not openai_api_key:
            raise ValueError('OPENAI_API_KEY environment variable is not set')

        self.model = ChatOpenAI(
            api_key=openai_api_key,
            model=model_name,
            # temperature=settings.openai_temperature,
            # max_retries=settings.openai_max_retries,
            # timeout=settings.openai_request_timeout,
        )
        self.encoding = tiktoken.encoding_for_model(model_name)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.encoding.encode(text))

    async def create_llm_chain(
        self,
        prompt_template: str,
        output_parser: Union[PydanticOutputParser, JsonOutputParser],
        is_chat_prompt: bool = False,
    ) -> RunnableSerializable:
        if is_chat_prompt:
            prompt = ChatPromptTemplate.from_messages(
                [('system', prompt_template)]
            )
        else:
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=[],
                partial_variables={
                    'format_instructions': (
                        output_parser.get_format_instructions()
                    )
                },
            )

        chain = prompt | self.model | output_parser
        return chain

    async def run_llm_chain(
        self,
        chain: RunnableSerializable,
        input_data: Dict[str, Any],
        user: User,
        exercise_type: ExerciseType,
        language_level: LanguageLevel,
    ) -> Any:
        try:
            logger.debug(f'LLM request data: {input_data}')
            input_text = str(input_data)
            input_tokens = self._count_tokens(input_text)
            response = await chain.ainvoke(input_data)
            response_text = str(response)
            output_tokens = self._count_tokens(response_text)
            logger.debug(f'LLM response: {response}')

            BACKEND_LLM_METRICS['input_tokens'].labels(
                exercise_type=exercise_type.value,
                level=language_level.value,
                user_language=user.user_language,
                target_language=user.target_language,
                llm_model=self.model.model_name,
            ).inc(input_tokens)

            BACKEND_LLM_METRICS['output_tokens'].labels(
                exercise_type=exercise_type.value,
                level=language_level.value,
                user_language=user.user_language,
                target_language=user.target_language,
                llm_model=self.model.model_name,
            ).inc(output_tokens)

            return response
        except ValidationError as e:
            logger.error(f'Validation error in LLM response: {e}')
            raise ValueError(f'Invalid response format from LLM: {e}') from e
        except GeneratorExit:
            logger.warning('LLM request was interrupted')
            raise
        except Exception as e:
            logger.error(f'Error during LLM request: {e}')
            raise RuntimeError(f'LLM service error: {e}') from e
