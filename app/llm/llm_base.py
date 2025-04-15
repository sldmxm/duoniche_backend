import logging
from typing import Any, Dict, TypeVar, Union

from langchain_core.output_parsers import (
    JsonOutputParser,
    PydanticOutputParser,
)
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseLLMService:
    def __init__(
        self,
        openai_api_key: str = settings.openai_api_key,
        model_name: str = settings.openai_main_model_name,
    ):
        if not openai_api_key:
            raise ValueError('OPENAI_API_KEY environment variable is not set')

        self.model = ChatOpenAI(
            api_key=openai_api_key,
            model=model_name,
        )

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
    ) -> Any:
        try:
            response = await chain.ainvoke(input_data)
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
