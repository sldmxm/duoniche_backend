import logging

import httpx

from app.config import settings
from app.core.interfaces.translate_provider import TranslateProvider
from app.metrics import BACKEND_TRANSLATOR_METRICS

logger = logging.getLogger(__name__)


class Translator(TranslateProvider):
    def __init__(
        self,
        google_api_key: str = settings.google_api_key,
    ):
        if not google_api_key:
            raise ValueError('GOOGLE_API_KEY environment variable is not set')
        self.google_api_key = google_api_key
        self.URL: str = (
            'https://translation.googleapis.com/language/translate/v2'
        )

    async def translate_text(self, text: str, target_language: str) -> str:
        request_data = {
            'q': text,
            'target': target_language,
        }
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.google_api_key,
        }
        try:
            with (
                BACKEND_TRANSLATOR_METRICS['translation_time']
                .labels(
                    target_language=target_language,
                )
                .time()
            ):
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        'post',
                        self.URL,
                        json=request_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    logger.info(f'Response: {response.json()}')
                    data = response.json()

                    BACKEND_TRANSLATOR_METRICS['translations'].labels(
                        target_language=target_language,
                    ).inc()
                    BACKEND_TRANSLATOR_METRICS['translations_chars'].labels(
                        target_language=target_language,
                    ).inc(len(text))

                    return data['data']['translations'][0]['translatedText']
        except httpx.HTTPStatusError as exc:
            error_text = (
                f'HTTP error with status code '
                f'{exc.response.status_code}: {exc}'
            )
            logger.error(error_text)
            raise
        except httpx.RequestError as exc:
            error_text = f'Request error: {exc}'
            logger.error(error_text)
            raise

    async def translate_feedback(
        self,
        feedback: str,
        user_language: str,
        exercise_data: str,
        user_answer: str,
        exercise_language: str,
    ) -> str:
        raise NotImplementedError
