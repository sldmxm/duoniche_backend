import asyncio
import logging
import unicodedata
from typing import List, Optional, Tuple

import httpx
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from lxml import html
from pydantic import BaseModel, Field

from app.core.consts import VOCABULARY_TAGS
from app.core.entities.exercise import Exercise
from app.core.entities.user_bot_profile import BotID
from app.core.enums import ExerciseType, LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.generation.persona import Persona
from app.core.texts import get_text
from app.core.value_objects.answer import Answer, ChooseAccentAnswer
from app.core.value_objects.exercise import ChooseAccentExerciseData
from app.llm.assessors.quality_assessor import ExerciseForAssessor
from app.llm.interfaces.exercise_generator import ExerciseGenerator
from app.llm.llm_base import BaseLLMService

logger = logging.getLogger(__name__)

BATCH_FETCH_NUM = 15
MIN_VOWELS = 2
MAX_VOWELS = 5
HTTPX_TIMEOUT = 10


class WordSuitabilityAssessment(BaseModel):
    word_to_assess: str = Field(
        description='The word that was assessed.',
    )
    is_common_and_suitable: bool = Field(
        description='True if the word is commonly used, widely known, '
        'and suitable for the specified language level.',
    )
    reasoning: str = Field(
        description='Brief explanation for the decision on commonness, '
        'suitability, and knownness.',
    )
    confidence_level: str = Field(
        description="Confidence in the assessment: 'HIGH', 'MEDIUM', 'LOW'.",
    )


class WordDefinitionAndExamples(BaseModel):
    meaning: str = Field(
        description='A concise dictionary-like definition of the word '
        'in the target language.'
    )
    examples: List[str] = Field(
        description='One or two example sentences using the word in'
        " the target language, appropriate for the learner's "
        'level.'
    )
    grammar_tags: dict = Field(
        description="A JSON object with key 'vocabulary' "
        'listing the topics covered in the exercise.'
    )


class ChooseAccentGenerationError(Exception):
    pass


class ChooseAccentGenerator(ExerciseGenerator):
    def __init__(
        self, llm_service: BaseLLMService, http_client: httpx.AsyncClient
    ):
        self.llm_service = llm_service
        self.http_client = http_client

    async def _assess_word_suitability_llm(
        self,
        word_no_accent: str,
        target_language_full_name: str,
        user_language_description: str,
        language_level: LanguageLevel,
    ) -> Optional[WordSuitabilityAssessment]:
        parser = PydanticOutputParser(
            pydantic_object=WordSuitabilityAssessment
        )
        system_prompt_template = (
            'You are an AI language expert. Your task is to assess a word '
            'from {target_language_full_name} for a '
            '{user_language_description}-speaking '
            'learner at the {language_level_value} level.\n'
            'Focus ONLY on how common, widely known, and generally suitable '
            'the word itself is for this level. '
            'Do NOT assess accent marking or specific grammatical nuances'
            ' unless they make the word unsuitable.\n'
            'Provide your confidence level in this assessment '
            "('HIGH', 'MEDIUM', 'LOW')."
        )
        user_prompt_template = (
            'Word to assess: {word_to_assess}\n\n'
            'Based on your knowledge of {target_language_full_name} and '
            'typical vocabulary for {language_level_value} learners:\n'
            '1. Is this word commonly used, widely known, and generally '
            'suitable for this level?\n'
            '2. Provide a brief reasoning for your decision.\n'
            '3. Provide a list of the vocabulary topics covered in a JSON '
            "object with key 'vocabulary' in the 'grammar_tags' field.\n"
            'Use the following tag list. Each tag either is or is not '
            'in the exercise:\n'
            f'Vocabulary Tags: {VOCABULARY_TAGS}\n'
            '4. What is your confidence level in this assessment '
            '(HIGH, MEDIUM, LOW)?\n\n'
            '{format_instructions}'
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
            'target_language_full_name': target_language_full_name,
            'user_language_description': user_language_description,
            'language_level_value': language_level.value,
            'word_to_assess': word_no_accent,
            'format_instructions': parser.get_format_instructions(),
        }
        try:
            assessment: WordSuitabilityAssessment = (
                await self.llm_service.run_llm_chain(chain, request_data)
            )
            return assessment
        except Exception as e:
            logger.error(
                f'Error during LLM word suitability assessment for '
                f"'{word_no_accent}': {e}",
                exc_info=True,
            )
            return None

    async def _get_word_definition_llm(
        self,
        word_no_accent: str,
        word_with_accent: str,
        target_language_full_name: str,
        language_level: LanguageLevel,
    ) -> Optional[WordDefinitionAndExamples]:
        parser = PydanticOutputParser(
            pydantic_object=WordDefinitionAndExamples
        )
        system_prompt_template = (
            'You are a helpful AI language assistant. Your task is to '
            'provide a dictionary-like entry '
            'for a word in {target_language_full_name} for a '
            '{language_level_value} learner. '
            'The definition and examples MUST be in '
            '{target_language_full_name}.'
        )
        user_prompt_template = (
            "For the {target_language_full_name} word '{word_to_define}'"
            " (the original form with accent is '{word_for_context}'):\n"
            '1. Provide a concise dictionary-like definition of '
            "'{word_to_define}' IN {target_language_full_name}. "
            'The definition should be simple and understandable for a '
            '{language_level_value} learner.\n'
            '2. Provide one or two simple example sentences using '
            "'{word_to_define}' IN {target_language_full_name}. "
            'The examples should also be suitable for a '
            '{language_level_value} learner and clearly illustrate '
            "the word's meaning.\n\n"
            '{format_instructions}'
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
            'target_language_full_name': target_language_full_name,
            'language_level_value': language_level.value,
            'word_to_define': word_no_accent,
            'word_for_context': word_with_accent,
            'format_instructions': parser.get_format_instructions(),
        }
        try:
            definition_and_examples: WordDefinitionAndExamples = (
                await self.llm_service.run_llm_chain(chain, request_data)
            )
            return definition_and_examples
        except Exception as e:
            logger.error(
                f'Error during LLM word definition generation for '
                f"'{word_no_accent}': {e}",
                exc_info=True,
            )
            return None

    async def _fetch_word_candidate(self) -> Optional[str]:
        try:
            resp = await self.http_client.get(
                'https://rechnik.chitanka.info/random',
                follow_redirects=True,
                timeout=HTTPX_TIMEOUT,
            )
            resp.raise_for_status()
            tree = html.fromstring(resp.text)
            word_elements = tree.xpath(
                '/html/body/div[2]/div[2]/div[1]/h2/span[1]'
            )
            if not word_elements:
                return None
            word = word_elements[0].text_content().strip()
            return word
        except httpx.RequestError as e:
            logger.error(
                f'HTTPX RequestError while fetching word candidate: {e}'
            )
        except html.etree.ParserError as e:
            logger.error(
                f'lxml ParserError while fetching word candidate: {e}'
            )
        except Exception as e:
            logger.error(
                f'Unexpected error while fetching word candidate: {e}',
                exc_info=True,
            )
        return None

    async def _fetch_word_candidates_batch(
        self, n: int = BATCH_FETCH_NUM
    ) -> List[str]:
        tasks = [self._fetch_word_candidate() for _ in range(n)]
        words_results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_words = []
        for i, res in enumerate(words_results):
            if isinstance(res, Exception):
                logger.error(f'Error in _fetch_word_candidate task {i}: {res}')
            elif isinstance(res, str):
                valid_words.append(res)
        return valid_words

    @staticmethod
    def _has_accent_nfd(word: str) -> bool:
        decomposed = unicodedata.normalize('NFD', word)
        return any(
            c in 'аеиоуъюя' and decomposed[i + 1] == '\u0300'
            for i, c in enumerate(decomposed.lower()[:-1])
        )

    @staticmethod
    def _get_accent_char_index_nfc(word_nfc: str) -> int:
        decomposed = unicodedata.normalize('NFD', word_nfc)
        for i, c in enumerate(decomposed.lower()[:-1]):
            if c in 'аеиоуъюя' and decomposed[i + 1] == '\u0300':
                return i
        return -1

    @staticmethod
    def _get_vowels_indexes_nfc(word_nfc: str) -> List[int]:
        return [i for i, c in enumerate(word_nfc.lower()) if c in 'аеиоуъюя']

    @staticmethod
    def _generate_incorrect_accents_nfc(
        word_with_accent_nfc: str,
    ) -> List[str]:
        original_accent_char_nfc_idx = (
            ChooseAccentGenerator._get_accent_char_index_nfc(
                word_with_accent_nfc
            )
        )

        word_nfd_chars = list(
            unicodedata.normalize('NFD', word_with_accent_nfc)
        )
        word_without_accent_nfd_chars = [
            c for c in word_nfd_chars if unicodedata.category(c) != 'Mn'
        ]
        word_without_accent_nfc = unicodedata.normalize(
            'NFC', ''.join(word_without_accent_nfd_chars)
        )

        res = []
        vowel_indices_in_nfc_no_accent = (
            ChooseAccentGenerator._get_vowels_indexes_nfc(
                word_without_accent_nfc
            )
        )

        for nfc_vowel_idx_no_accent in vowel_indices_in_nfc_no_accent:
            if nfc_vowel_idx_no_accent == original_accent_char_nfc_idx:
                continue

            temp_nfd_word_list_no_accent = list(
                unicodedata.normalize('NFD', word_without_accent_nfc)
            )

            nfd_insert_after_idx = -1
            current_nfd_len_sum = 0
            for i_nfc, char_nfc_val in enumerate(word_without_accent_nfc):
                char_nfd_segment = unicodedata.normalize('NFD', char_nfc_val)
                if i_nfc == nfc_vowel_idx_no_accent:
                    nfd_insert_after_idx = (
                        current_nfd_len_sum + len(char_nfd_segment) - 1
                    )
                    break
                current_nfd_len_sum += len(char_nfd_segment)

            if nfd_insert_after_idx != -1 and (
                nfd_insert_after_idx + 1
            ) <= len(temp_nfd_word_list_no_accent):
                incorrect_word_nfd_list = (
                    temp_nfd_word_list_no_accent[: nfd_insert_after_idx + 1]
                    + ['\u0300']
                    + temp_nfd_word_list_no_accent[nfd_insert_after_idx + 1 :]
                )
                incorrect_word_nfc = unicodedata.normalize(
                    'NFC', ''.join(incorrect_word_nfd_list)
                )
                if (
                    incorrect_word_nfc != word_with_accent_nfc
                ):  # Ensure it's different
                    res.append(incorrect_word_nfc)
        return list(set(res))

    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, Answer, ExerciseForAssessor]:
        if target_language != BotID.BG.value:
            raise ChooseAccentGenerationError(
                f'Skipping CHOOSE_ACCENT for non-BG language: '
                f'{target_language}'
            )

        word_candidates = await self._fetch_word_candidates_batch()

        if not word_candidates:
            logger.warning(
                'Failed to fetch any word candidates for '
                'accent exercise generation.'
            )
            raise ChooseAccentGenerationError(
                'Failed to fetch any word candidates.'
            )

        for word_with_accent_candidate in word_candidates:
            word_with_accent_nfc = unicodedata.normalize(
                'NFC', word_with_accent_candidate
            )

            if not ChooseAccentGenerator._has_accent_nfd(word_with_accent_nfc):
                logger.info(
                    f"Word candidate '{word_with_accent_nfc}' skipped "
                    f'(initial validation: word has no accent).'
                )
                continue

            vowel_count = len(
                ChooseAccentGenerator._get_vowels_indexes_nfc(
                    word_with_accent_nfc
                )
            )
            if not MIN_VOWELS <= vowel_count <= MAX_VOWELS:
                logger.info(
                    f"Word candidate '{word_with_accent_nfc}' skipped "
                    f'(initial validation: {vowel_count=}).'
                )
                continue

            word_no_accent = ''.join(
                c
                for c in unicodedata.normalize('NFD', word_with_accent_nfc)
                if unicodedata.category(c) != 'Mn'
            )

            suitability_assessment = await self._assess_word_suitability_llm(
                word_no_accent,
                target_language,
                user_language,
                language_level,
            )

            if (
                not suitability_assessment
                or not suitability_assessment.is_common_and_suitable
                or suitability_assessment.confidence_level == 'LOW'
            ):
                reason = (
                    suitability_assessment.reasoning
                    if suitability_assessment
                    else 'LLM assessment failed'
                )
                conf_level = (
                    suitability_assessment.confidence_level
                    if suitability_assessment
                    else 'N/A'
                )
                logger.info(
                    f"Word '{word_no_accent}' skipped by LLM suitability: "
                    f'{reason} (Confidence: {conf_level}).'
                )
                continue
            logger.info(
                f"Word '{word_no_accent}' passed LLM suitability "
                f'(Confidence: {suitability_assessment.confidence_level}). '
                f'Reason: {suitability_assessment.reasoning}'
            )

            definition_and_examples = await self._get_word_definition_llm(
                word_no_accent,
                word_with_accent_nfc,
                target_language,
                language_level,
            )

            if (
                not definition_and_examples
                or not definition_and_examples.meaning
            ):
                logger.warning(
                    f'LLM failed to generate definition for '
                    f"'{word_no_accent}', skipping."
                )
                continue

            formatted_meaning = f'Значение: {definition_and_examples.meaning}'
            if definition_and_examples.examples:
                formatted_meaning += '\nПримери:\n' + '\n'.join(
                    f'- {ex}' for ex in definition_and_examples.examples
                )
            logger.info(
                f"LLM generated meaning for '{word_no_accent}': "
                f'{formatted_meaning[:100]}...'
            )

            incorrect_options = (
                ChooseAccentGenerator._generate_incorrect_accents_nfc(
                    word_with_accent_nfc
                )
            )
            if not incorrect_options or len(incorrect_options) < 1:
                logger.warning(
                    f'Could not generate sufficient incorrect accent '
                    f"options for '{word_with_accent_nfc}', skipping."
                )
                continue

            all_options = [word_with_accent_nfc] + incorrect_options

            grammar_tags = definition_and_examples.grammar_tags
            grammar_tags['grammar'] = grammar_tags.get('grammar', []) + [
                'accent'
            ]

            exercise = Exercise(
                exercise_id=None,
                exercise_type=ExerciseType.CHOOSE_ACCENT,
                exercise_language=target_language,
                language_level=language_level,
                topic=ExerciseTopic.GENERAL,
                exercise_text=get_text(
                    ExerciseType.CHOOSE_ACCENT, user_language_code
                ),
                grammar_tags=grammar_tags,
                data=ChooseAccentExerciseData(
                    options=all_options,
                    meaning=formatted_meaning,
                ),
            )
            correct_answer_obj = ChooseAccentAnswer(
                answer=word_with_accent_nfc
            )

            exercise_for_assessor = ExerciseForAssessor(
                text=exercise.exercise_text,
                options=all_options,
                correct_answer=word_with_accent_nfc,
                correct_options=[word_with_accent_nfc],
                incorrect_options=incorrect_options,
                exercise_type=ExerciseType.CHOOSE_ACCENT,
                language_level=language_level,
            )

            logger.info(
                f'Generated CHOOSE_ACCENT exercise for word: '
                f'{word_with_accent_nfc}'
            )
            return exercise, correct_answer_obj, exercise_for_assessor

        logger.warning(
            'Failed to generate a suitable CHOOSE_ACCENT '
            'exercise after all checks.'
        )
        raise ChooseAccentGenerationError(
            'No suitable word found after all processing steps.'
        )
