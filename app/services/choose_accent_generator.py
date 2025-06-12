import asyncio
import json
import logging
import unicodedata
import urllib
from typing import List, Optional, Tuple

import httpx
from lxml import html

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.user_bot_profile import BotID
from app.core.enums import ExerciseType
from app.core.generation.config import ExerciseTopic
from app.core.texts import get_text
from app.core.value_objects.answer import Answer, ChooseAccentAnswer
from app.core.value_objects.exercise import ChooseAccentExerciseData

logger = logging.getLogger(__name__)

BATCH_FETCH_NUM = 5

MIN_VOWELS = 2
MAX_VOWELS = 5
MIN_MEANING_LEN = 10
MIN_WORD_RANK = 11000

HTTPX_TIMEOUT = 10

UNDESIRED_MARKERS = {
    'хим.',
    'мед.',
    'остар.',
    'спец.',
    'физ.',
    'техн.',
    'мат.',
    'книж.',
    'поет.',
    'диал.',
    'остаряло',
    'рядко',
}

TALKOVEN_NOT_FOUND_STR = {
    'Вероятно сте искали да изпишете',
    'Няма намерени подобни думи в речника',
}


class ChooseAccentGenerationError(Exception):
    pass


class ChooseAccentGenerator:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client
        self.wortschatz_news_base_url = (
            'https://api.wortschatz-leipzig.de/ws/words/'
            'bul_news_2011_1M/word/'
        )
        self.wortschatz_wikipedia_base_url = (
            'https://api.wortschatz-leipzig.de/ws/words/'
            'bul_wikipedia_2018_1M/word/'
        )
        self.talkoven_base_url = 'https://talkoven.onlinerechnik.com/duma/'

    async def fetch_word_rank(self, word: str, url: str) -> Optional[int]:
        """Fetches word frequency from Wortschatz Leipzig API."""
        word_normalized = unicodedata.normalize('NFC', word)
        word_no_accent = ''.join(
            c
            for c in unicodedata.normalize('NFD', word_normalized)
            if unicodedata.category(c) != 'Mn'
        )
        try:
            encoded_word = urllib.parse.quote(word_no_accent)
            url = f'{url}{encoded_word}'
            response = await self.http_client.get(
                url,
                headers={'accept': 'application/json'},
                timeout=HTTPX_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return data.get('wordRank')
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(
                    f"Word '{word_no_accent}' not found in "
                    f'Wortschatz Leipzig. Assuming low frequency.'
                )
                return 0
            logger.error(
                f"HTTP error fetching frequency for '{word_no_accent}': "
                f'{e.response.status_code} - {e.response.text}'
            )
        except httpx.RequestError as e:
            logger.error(
                f"Request error fetching frequency for '{word_no_accent}': {e}"
            )
        except json.JSONDecodeError as e:
            logger.error(
                f'JSON decode error for frequency response of '
                f"'{word_no_accent}': {e}"
            )
        except Exception as e:
            logger.error(
                f'Unexpected error fetching frequency for '
                f"'{word_no_accent}': {e}",
                exc_info=True,
            )
        return None

    async def fetch_word_markers_from_talkoven(
        self, word_no_accent: str
    ) -> Optional[str]:
        """Fetches the first paragraph from talkoven.onlinerechnik.com
        to check for markers."""
        try:
            encoded_word = urllib.parse.quote(word_no_accent.lower())
            url = f'{self.talkoven_base_url}{encoded_word}'
            response = await self.http_client.get(url, timeout=HTTPX_TIMEOUT)
            response.raise_for_status()
            tree = html.fromstring(response.text)
            paragraph_elements = tree.xpath('//*[@id="maintext"]/p[1]')
            if not paragraph_elements:
                paragraph_elements = tree.xpath('/html/body/div/div[2]/p[1]')

            if paragraph_elements:
                paragraph_text = paragraph_elements[0].text_content().strip()
                logger.debug(
                    f"Talkoven paragraph for '{word_no_accent}': "
                    f'{paragraph_text[:200]}'
                )
                return paragraph_text
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug(f"Word '{word_no_accent}' not found on Talkoven.")
            else:
                logger.error(
                    f'HTTP error fetching markers for '
                    f"'{word_no_accent}' from Talkoven: "
                    f'{e.response.status_code} - {e.response.text}'
                )
        except httpx.RequestError as e:
            logger.error(
                f"Request error fetching markers for '{word_no_accent}' "
                f'from Talkoven: {e}'
            )
        except Exception as e:
            logger.error(
                f'Unexpected error fetching markers for '
                f"'{word_no_accent}' from Talkoven: {e}",
                exc_info=True,
            )
        return None

    async def fetch_word(
        self,
    ) -> Optional[Tuple[str, str]]:
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
            meaning_elements = tree.xpath(
                '/html/body/div[2]/div[2]/div[1]/div[1]/div'
            )
            if not word_elements:
                return None
            word = word_elements[0].text_content().strip()
            meaning = meaning_elements[0].text_content().strip()
            return word, meaning

        except httpx.RequestError as e:
            logger.error(f'HTTPX RequestError while fetching word: {e}')
        except html.etree.ParserError as e:
            logger.error(f'lxml ParserError while fetching word: {e}')
        except Exception as e:
            logger.error(
                f'Unexpected error while fetching word: {e}', exc_info=True
            )
        return None

    async def fetch_words_batch(
        self,
        n: int = BATCH_FETCH_NUM,
    ) -> List[Tuple[str, str]]:
        tasks = [self.fetch_word() for _ in range(n)]
        words_results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_words = []
        for i, res in enumerate(words_results):
            if isinstance(res, Exception):
                logger.error(f'Error in fetch_word task {i}: {res}')
            elif isinstance(res, tuple):
                valid_words.append(res)
        return valid_words

    @staticmethod
    def has_accent_nfd(word: str) -> bool:
        decomposed = unicodedata.normalize('NFD', word)
        return any(
            c in 'аеиоуъюя' and decomposed[i + 1] == '\u0300'
            for i, c in enumerate(decomposed.lower()[:-1])
        )

    @staticmethod
    def get_accent_index(word: str) -> int:
        decomposed = unicodedata.normalize('NFD', word)
        for i, c in enumerate(decomposed.lower()[:-1]):
            if c in 'аеиоуъюя' and decomposed[i + 1] == '\u0300':
                return i
        return -1

    @staticmethod
    def get_vowels_indexes(word: str) -> List[int]:
        word = unicodedata.normalize('NFD', word)
        return [i for i, c in enumerate(word.lower()) if c in 'аеиоуъюя']

    @staticmethod
    def generate_incorrect_accents(word: str) -> List[str]:
        vowels_indexes = ChooseAccentGenerator.get_vowels_indexes(word)
        accent_index = ChooseAccentGenerator.get_accent_index(word)
        word_without_accent = (
            word[: accent_index + 1] + word[accent_index + 2 :]
        )
        res = []
        for vowel_idx in vowels_indexes:
            if vowel_idx == accent_index:
                continue
            elif vowel_idx < accent_index:
                incorrect_accent_idx = vowel_idx + 1
            else:
                incorrect_accent_idx = vowel_idx
            incorrect_word = (
                word_without_accent[:incorrect_accent_idx]
                + '\u0300'
                + word_without_accent[incorrect_accent_idx:]
            )
            res.append(incorrect_word)
        return res

    async def generate(
        self,
        user_language,
    ) -> Tuple[Exercise, Answer]:
        words_data = await self.fetch_words_batch(BATCH_FETCH_NUM)

        if not words_data:
            logger.warning(
                'Failed to fetch any words for accent exercise generation.'
            )
            raise ChooseAccentGenerationError('Failed to fetch any words.')

        for word, _ in words_data:
            # TODO: проверка, что ударение совпадает с официальным словарем
            #  или хотя бы talkoven

            if not (
                ChooseAccentGenerator.has_accent_nfd(word)
                and MIN_VOWELS
                <= len(ChooseAccentGenerator.get_vowels_indexes(word))
                <= MAX_VOWELS
            ):
                logger.debug(
                    f"Word '{word}' skipped due to initial validation"
                    f' (accent, vowels).'
                )
                continue

            word_normalized_nfc = unicodedata.normalize('NFC', word)
            word_no_accent = ''.join(
                c
                for c in unicodedata.normalize('NFD', word_normalized_nfc)
                if unicodedata.category(c) != 'Mn'
            )

            talkoven_paragraph = await self.fetch_word_markers_from_talkoven(
                word_no_accent
            )
            if talkoven_paragraph:
                if any(
                    marker in talkoven_paragraph.lower()
                    for marker in UNDESIRED_MARKERS
                ):
                    logger.debug(
                        f"Word '{word}' skipped due to undesired marker "
                        f'found on Talkoven: '
                        f"'{next((m for m in UNDESIRED_MARKERS
                                  if m in talkoven_paragraph.lower()),
                                 None)}'."
                    )
                    continue
                if any(
                    not_found_str in talkoven_paragraph
                    for not_found_str in TALKOVEN_NOT_FOUND_STR
                ):
                    logger.debug(
                        f"Word '{word}' skipped due not found on Talkoven."
                    )
                    continue

                if len(talkoven_paragraph) < MIN_MEANING_LEN:
                    logger.debug(
                        f"Word '{word}' skipped due to short meaning "
                        f"from Talkoven: '{talkoven_paragraph}'"
                    )
                    continue
                meaning_to_use = talkoven_paragraph
            else:
                logger.debug(
                    f"Word '{word}' skipped as no valid meaning "
                    f'was retrieved from Talkoven.'
                )
                continue

            word_news_rank = await self.fetch_word_rank(
                word, url=self.wortschatz_news_base_url
            )
            word_wikipedia_rank = await self.fetch_word_rank(
                word, url=self.wortschatz_wikipedia_base_url
            )
            if word_news_rank is None or word_wikipedia_rank is None:
                logger.warning(
                    f"Could not determine word_rank for '{word}', skipping."
                )
                continue
            if (
                word_news_rank > MIN_WORD_RANK
                or word_wikipedia_rank > MIN_WORD_RANK
            ):
                logger.debug(
                    f"Word '{word}' skipped due to low word_rank "
                    f'(news: {word_news_rank}, wiki: {word_wikipedia_rank}).'
                )
                continue

            logger.info(
                f"Word '{word}' passed all checks (markers, rank). "
                f"Meaning from Talkoven: '{meaning_to_use}'."
            )

            incorrect_options = self.generate_incorrect_accents(word)
            if not incorrect_options:
                logger.warning(
                    f'Could not generate incorrect accent options for '
                    f"'{word}', skipping."
                )
                continue

            all_options = [word] + incorrect_options

            exercise = Exercise(
                exercise_id=None,
                exercise_type=ExerciseType.CHOOSE_ACCENT,
                exercise_language=BotID.BG.value,
                language_level=settings.default_language_level,
                topic=ExerciseTopic.GENERAL,
                exercise_text=get_text(
                    ExerciseType.CHOOSE_ACCENT, user_language
                ),
                data=ChooseAccentExerciseData(
                    options=all_options,
                    meaning=meaning_to_use,
                ),
            )
            correct_answer = ChooseAccentAnswer(answer=word)
            logger.info(
                f'Generated exercise: {exercise} with correct answer: {word}'
            )
            return exercise, correct_answer

        logger.warning(
            'Failed to generate a suitable CHOOSE_ACCENT exercise '
            'after checking all fetched words.'
        )
        raise ChooseAccentGenerationError(
            'Failed to generate a suitable exercise from fetched words.'
        )


async def gen():
    async with httpx.AsyncClient() as client:
        generator = ChooseAccentGenerator(client)
        try:
            exercise, answer = await generator.generate('ru')
            print('Generated Exercise:')
            print(exercise.model_dump_json(indent=2))
            print('\nCorrect Answer:')
            print(answer.model_dump_json(indent=2))
        except ChooseAccentGenerationError as e:
            print(f'Error: {e}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(gen())
