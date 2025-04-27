import asyncio
import logging
import unicodedata
from typing import List, Optional, Tuple

import httpx
from lxml import html

from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, ExerciseType
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
    @staticmethod
    async def fetch_word(
        client: httpx.AsyncClient,
    ) -> Optional[Tuple[str, str]]:
        try:
            resp = await client.get(
                'https://rechnik.chitanka.info/random', follow_redirects=True
            )
            tree = html.fromstring(resp.text)
            word = tree.xpath('/html/body/div[2]/div[2]/div[1]/h2/span[1]')
            meaning = tree.xpath('/html/body/div[2]/div[2]/div[1]/div[1]/div')
            if not word:
                return None
            return word[0].text_content().strip(), meaning[
                0
            ].text_content().strip()
        except Exception as e:
            logger.error(f'Error while fetching word: {e}')
        return None

    @staticmethod
    async def fetch_words_batch(
        n: int = BATCH_FETCH_NUM,
    ) -> List[Tuple[str, str]]:
        async with httpx.AsyncClient(timeout=HTTPX_TIMEOUT) as client:
            tasks = [
                ChooseAccentGenerator.fetch_word(client) for _ in range(n)
            ]
            words = await asyncio.gather(*tasks)
            return [w for w in words if w]

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

    @staticmethod
    async def generate(
        user_language,
    ) -> Optional[Tuple[Exercise, Answer]]:
        words = await ChooseAccentGenerator.fetch_words_batch(BATCH_FETCH_NUM)
        for word, meaning in words:
            is_ok = (
                ChooseAccentGenerator.has_accent_nfd(word)
                and MIN_VOWELS
                <= len(ChooseAccentGenerator.get_vowels_indexes(word))
                <= MAX_VOWELS
                and len(meaning) > MIN_MEANING_LEN
                and 'остар.' not in meaning.lower()
            )
            if is_ok:
                exercise = Exercise(
                    exercise_id=None,
                    exercise_type=ExerciseType.CHOOSE_ACCENT,
                    exercise_language='Bulgarian',
                    language_level=DEFAULT_LANGUAGE_LEVEL,
                    topic=ExerciseTopic.GENERAL,
                    exercise_text=get_text(
                        ExerciseType.CHOOSE_ACCENT, user_language
                    ),
                    data=ChooseAccentExerciseData(
                        options=[word]
                        + ChooseAccentGenerator.generate_incorrect_accents(
                            word
                        ),
                    ),
                )
                correct_answer = ChooseAccentAnswer(answer=word)
                logger.info(f'Generated exercise: {exercise}')
                return exercise, correct_answer
        logger.warning('Failed to generate exercise')
        raise ChooseAccentGenerationError('Failed to generate exercise')


async def gen():
    print(await ChooseAccentGenerator.generate('ru'))


if __name__ == '__main__':
    asyncio.run(gen())
