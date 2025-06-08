import asyncio
import base64
import logging
import subprocess
import tempfile
from typing import Optional

import httpx
from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleTTSService:
    def __init__(
        self,
        api_key: str = settings.google_api_key,
        tts_model: str = settings.tts_model,
        proxy_url: Optional[str] = settings.google_tts_proxy_url,
    ):
        if not api_key:
            logger.error('GOOGLE_API_KEY is not set for TTSService')
            raise ValueError('GOOGLE_API_KEY is not set for TTSService')
        if not tts_model:
            logger.error('TTS_MODEL is not set for TTSService')
            raise ValueError('TTS_MODEL is not set for TTSService')
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.tts_model_name = tts_model

        self.default_voice_config = types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name='Leda',
            ),
        )
        self.default_speech_config = types.SpeechConfig(
            voice_config=self.default_voice_config,
        )
        self.gemini_sample_rate = 24000
        self.opus_target_sample_rate = 48000

        if proxy_url:
            self._http_client = httpx.AsyncClient(
                proxy=proxy_url, timeout=30.0
            )
            logger.info('GoogleTTSService initialized REST client with proxy')
        else:
            self._http_client = httpx.AsyncClient(timeout=30.0)
            logger.info(
                'GoogleTTSService initialized REST client without proxy '
                '(proxy_url not set).'
            )

    async def close_rest_http_client(self):
        """Closes the internally created httpx.AsyncClient for REST calls."""
        if self._http_client:
            await self._http_client.aclose()
            logger.info('GoogleTTSService: Closed internal REST HTTP client.')

    async def _convert_pcm_to_ogg_opus(self, pcm_data: bytes) -> bytes | None:
        """
        Converts raw PCM data to OGG Opus using FFmpeg.
        Assumes PCM data is 16-bit signed little-endian, mono.
        """
        try:
            with (
                tempfile.NamedTemporaryFile(
                    suffix='.raw',
                    delete=True,
                ) as pcm_file,
                tempfile.NamedTemporaryFile(
                    suffix='.ogg',
                    delete=True,
                ) as ogg_file,
            ):
                pcm_file.write(pcm_data)
                pcm_file.flush()

                ffmpeg_command = [
                    'ffmpeg',
                    '-f',
                    's16le',
                    '-ar',
                    str(self.gemini_sample_rate),
                    '-ac',
                    '1',
                    '-i',
                    pcm_file.name,
                    '-c:a',
                    'libopus',
                    '-b:a',
                    '64k',
                    '-vbr',
                    'on',
                    '-ar',
                    str(self.opus_target_sample_rate),
                    '-y',
                    ogg_file.name,
                ]

                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    logger.error(
                        f'FFmpeg conversion failed. '
                        f'Return code: {process.returncode}',
                    )
                    logger.error(
                        f"FFmpeg stderr: " f"{stderr.decode(errors='ignore')}",
                    )
                    return None

                with open(ogg_file.name, 'rb') as f_out:
                    return f_out.read()

        except FileNotFoundError:
            logger.error(
                'FFmpeg not found. Please ensure FFmpeg '
                'is installed and in PATH.',
            )
            return None
        except Exception as e:
            logger.error(
                f'Error during PCM to OGG Opus conversion: ' f'{e}',
                exc_info=True,
            )
            return None

    async def _text_to_speech_rest_api(
        self,
        text: str,
        voice_name: str = 'Leda',
    ) -> bytes | None:
        """
        Generates speech using Google's REST API for TTS with httpx,
        supporting proxy.
        Returns raw PCM audio data.
        """
        if not self._http_client:
            logger.error(
                'HTTP client not available for REST API call in TTSService.'
            )
            return None

        api_url = (
            f'https://generativelanguage.googleapis.com/v1beta/models/'
            f'{self.tts_model_name}:generateContent?key={self.api_key}'
        )

        payload = {
            'contents': [{'parts': [{'text': text}]}],
            'generationConfig': {
                'responseModalities': ['AUDIO'],
                'speechConfig': {
                    'voiceConfig': {
                        'prebuiltVoiceConfig': {'voiceName': voice_name}
                    }
                },
            },
            'model': self.tts_model_name,
        }
        headers = {
            'Content-Type': 'application/json',
        }

        try:
            logger.info(
                f'Sending TTS request to: {api_url} via REST API (fallback)'
            )

            response = await self._http_client.post(
                api_url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()
            response_data = response.json()

            if (
                response_data.get('candidates')
                and response_data['candidates'][0]
                .get('content', {})
                .get('parts')
                and response_data['candidates'][0]['content']['parts'][0]
                .get('inlineData', {})
                .get('data')
            ):
                audio_data_base64 = response_data['candidates'][0]['content'][
                    'parts'
                ][0]['inlineData']['data']
                pcm_data = base64.b64decode(audio_data_base64)
                logger.info(
                    f'Successfully received PCM data via REST API. '
                    f'Length: {len(pcm_data)}'
                )
                return pcm_data
            else:
                logger.error(
                    f'Unexpected response structure from Google TTS REST API: '
                    f'{response_data}'
                )
                return None

        except httpx.HTTPStatusError as e:
            logger.error(
                f'HTTP error calling Google TTS REST API: '
                f'{e.response.status_code} - {e.response.text}'
            )
            logger.error(f'Request payload for REST API: {payload}')
            return None
        except Exception as e:
            logger.error(
                f'Error during Google TTS REST API request: {e}', exc_info=True
            )
            return None

    async def text_to_speech_ogg(
        self,
        text: str,
        voice_name: str | None = None,
        emotion_instruction: Optional[str] = None,
    ) -> bytes | None:
        """
        Converts text to speech and returns OGG Opus audio data as bytes.
        Returns None if generation fails.
        """
        text_to_synthesize = text
        if emotion_instruction:
            text_to_synthesize = f'{emotion_instruction.strip()} {text}'

        current_voice_name = voice_name if voice_name else 'Leda'
        pcm_data: Optional[bytes] = None

        try:
            logger.info(
                f"Synthesizing speech for: '{text_to_synthesize[:100]}...' "
                f'using genai SDK'
            )
            speech_config_to_use = self.default_speech_config
            if voice_name:
                current_voice_config = types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    ),
                )
                speech_config_to_use = types.SpeechConfig(
                    voice_config=current_voice_config,
                )

            request_config = types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=speech_config_to_use,
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.tts_model_name,
                contents=text_to_synthesize,
                config=request_config,
            )

            if (
                not response.candidates
                or not response.candidates[0].content.parts
            ):
                logger.error(
                    'TTS generation failed (SDK): '
                    'No content in response from Google GenAI'
                )
            elif (
                not response.candidates[0].content.parts[0].inline_data
                or not response.candidates[0].content.parts[0].inline_data.data
            ):
                logger.error(
                    'TTS generation failed (SDK): '
                    'No inline audio data in response part'
                )
            else:
                pcm_data = (
                    response.candidates[0].content.parts[0].inline_data.data
                )
                logger.info('Successfully received PCM data via genai SDK. ')

        except Exception as e:
            if 'User location is not supported' in str(e):
                logger.warning(
                    f'TTS generation via SDK failed due to location error: '
                    f'{e}. '
                    f'Falling back to REST API with proxy (if configured).'
                )
                pcm_data = await self._text_to_speech_rest_api(
                    text=text_to_synthesize, voice_name=current_voice_name
                )
            else:
                logger.error(
                    f'Error during TTS generation via SDK: {e}',
                    exc_info=True,
                )

        if not pcm_data:
            logger.error(
                'TTS generation failed: '
                'No PCM data received after all attempts'
            )
            return None

        ogg_data = await self._convert_pcm_to_ogg_opus(pcm_data)

        if ogg_data:
            logger.info(
                f'Successfully generated and converted TTS audio '
                f"for text: '{text[:50]}...'"
            )
        else:
            logger.error(
                f'Failed to convert PCM to OGG Opus for text: '
                f"'{text[:50]}...'"
            )
        return ogg_data


if __name__ == '__main__':
    import asyncio
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    )

    load_dotenv()

    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    TTS_MODEL = os.getenv('TTS_MODEL')
    GOOGLE_TTS_PROXY_URL_TEST = os.getenv('GOOGLE_TTS_PROXY_URL')

    async def main_test():
        logger.info('Starting TTS service test with fallback logic...')

        if not GOOGLE_API_KEY or not TTS_MODEL:
            logger.error(
                'GOOGLE_API_KEY or TTS_MODEL is not set. '
                'Please check your .env file.'
            )
            return

        test_http_client = None
        if GOOGLE_TTS_PROXY_URL_TEST:
            test_http_client = httpx.AsyncClient(
                proxy=GOOGLE_TTS_PROXY_URL_TEST, timeout=30.0
            )

        tts_service = GoogleTTSService(
            api_key=GOOGLE_API_KEY,
            tts_model=TTS_MODEL,
            proxy_url=GOOGLE_TTS_PROXY_URL_TEST,
        )

        sample_text_bg = (
            'Днес времето беше слънчево и приятно, идеално за разходка '
            'в парка. Купих си кафе от малко местно кафене и седнах на '
            'пейка да почета. Хората около мен изглеждаха спокойни '
            'и усмихнати.'
        )

        emotion_instruction_example = 'Say cheerfully:'

        full_text_for_tts = f'{emotion_instruction_example} {sample_text_bg}'
        logger.info(
            f'Attempting to generate speech with emotion for: '
            f"'{full_text_for_tts}'"
        )
        ogg_audio_data = await tts_service.text_to_speech_ogg(
            text=sample_text_bg,
            emotion_instruction=emotion_instruction_example,
        )

        if ogg_audio_data:
            output_dir = Path(__file__).parent.parent / 'tests' / 'temp'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = output_dir / 'test_tts_output_fallback.ogg'

            try:
                with open(output_file_path, 'wb') as f:
                    f.write(ogg_audio_data)
                logger.info(
                    f'Successfully generated OGG audio via fallback '
                    f'logic and saved to: '
                    f'{output_file_path.resolve()}'
                )
                logger.info(f'File size: {len(ogg_audio_data)} bytes')
            except IOError as e:
                logger.error(f'Failed to write audio file: {e}')
        else:
            logger.error(
                'Failed to generate OGG audio data via fallback logic.'
            )

        if test_http_client:
            await test_http_client.aclose()

        logger.info('TTS service fallback logic test finished.')

    asyncio.run(main_test())
