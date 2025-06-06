import asyncio
import logging
import unicodedata
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
HTTPX_TIMEOUT = 10
MIN_VOWELS = 2
MAX_VOWELS = 5
MIN_MEANING_LEN = 10


class ChooseAccentGenerationError(Exception):
    pass


class ChooseAccentGenerator:
    def __init__(self, http_client: httpx.AsyncClient):  # <--- Конструктор
        self.http_client = http_client

    async def fetch_word(
        self,
    ) -> Optional[Tuple[str, str]]:
        try:
            resp = await self.http_client.get(
                'https://rechnik.chitanka.info/random', follow_redirects=True
            )
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

        for word, meaning in words_data:
            is_ok = (
                ChooseAccentGenerator.has_accent_nfd(word)
                and MIN_VOWELS
                <= len(ChooseAccentGenerator.get_vowels_indexes(word))
                <= MAX_VOWELS
                and len(meaning) >= MIN_MEANING_LEN
                and 'остар.' not in meaning.lower()
                and 'спец.' not in meaning.lower()
            )
            if is_ok:
                incorrect_options = self.generate_incorrect_accents(word)
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
                    ),
                )
                correct_answer = ChooseAccentAnswer(answer=word)
                logger.info(f'Generated exercise: {exercise}')
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
            print(exercise)
            print(answer)
        except ChooseAccentGenerationError as e:
            print(e)


if __name__ == '__main__':
    asyncio.run(gen())
