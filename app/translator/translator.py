import logging

import httpx

from app.config import settings
from app.core.interfaces.translate_provider import TranslateProvider

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
        url_with_key = f'{self.URL}?key={self.google_api_key}'
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    'post',
                    url_with_key,
                    json=request_data,
                )
                response.raise_for_status()
                logger.debug(f'Response: {response.json()}')
                data = response.json()
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
