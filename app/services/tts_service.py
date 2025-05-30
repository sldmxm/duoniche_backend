import asyncio
import logging
import subprocess
import tempfile

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


class GoogleTTSService:
    def __init__(
        self,
        api_key: str = settings.google_api_key,
        tts_model: str = settings.tts_model,
    ):
        if not api_key:
            logger.error('GOOGLE_API_KEY is not set for TTSService')
            raise ValueError('GOOGLE_API_KEY is not set for TTSService')
        if not tts_model:
            logger.error('TTS_MODEL is not set for TTSService')
            raise ValueError('TTS_MODEL is not set for TTSService')

        self.client = genai.Client(api_key=api_key)
        self.tts_model_name = tts_model

        self.default_voice_config = types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name='Leda',
            )
        )
        self.default_speech_config = types.SpeechConfig(
            voice_config=self.default_voice_config
        )
        self.gemini_sample_rate = 24000
        self.opus_target_sample_rate = 48000

    async def _convert_pcm_to_ogg_opus(self, pcm_data: bytes) -> bytes | None:
        """
        Converts raw PCM data to OGG Opus using FFmpeg.
        Assumes PCM data is 16-bit signed little-endian, mono.
        """
        try:
            with (
                tempfile.NamedTemporaryFile(
                    suffix='.raw', delete=True
                ) as pcm_file,
                tempfile.NamedTemporaryFile(
                    suffix='.ogg', delete=True
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
                        f'Return code: {process.returncode}'
                    )
                    logger.error(
                        f"FFmpeg stderr: " f"{stderr.decode(errors='ignore')}"
                    )
                    return None

                with open(ogg_file.name, 'rb') as f_out:
                    return f_out.read()

        except FileNotFoundError:
            logger.error(
                'FFmpeg not found. Please ensure FFmpeg '
                'is installed and in PATH.'
            )
            return None
        except Exception as e:
            logger.error(
                f'Error during PCM to OGG Opus conversion: ' f'{e}',
                exc_info=True,
            )
            return None

    async def text_to_speech_ogg(
        self, text: str, voice_name: str | None = None
    ) -> bytes | None:
        """
        Converts text to speech and returns OGG Opus audio data as bytes.
        Returns None if generation fails.
        """
        try:
            speech_config_to_use = self.default_speech_config
            if voice_name:
                current_voice_config = types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
                speech_config_to_use = types.SpeechConfig(
                    voice_config=current_voice_config
                )

            request_config = types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=speech_config_to_use,
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.tts_model_name,
                contents=text,
                config=request_config,
            )

            if (
                not response.candidates
                or not response.candidates[0].content.parts
            ):
                logger.error(
                    'TTS generation failed: '
                    'No content in response from Google GenAI'
                )
                return None

            audio_part = response.candidates[0].content.parts[0]
            if not audio_part.inline_data or not audio_part.inline_data.data:
                logger.error(
                    'TTS generation failed: '
                    'No inline audio data in response part'
                )
                return None

            pcm_data = audio_part.inline_data.data

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

        except Exception as e:
            logger.error(
                f'Error during TTS generation or conversion: {e}',
                exc_info=True,
            )
            return None


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

    async def main_test():
        logger.info('Starting TTS service test...')

        tts_service = GoogleTTSService(
            api_key=GOOGLE_API_KEY, tts_model=TTS_MODEL
        )

        sample_text_bg = (
            'Днес времето беше слънчево и приятно, идеално за разходка '
            'в парка. Купих си кафе от малко местно кафене и седнах на '
            'пейка да почета. Хората около мен изглеждаха спокойни '
            'и усмихнати.'
        )

        logger.info(f"Attempting to generate speech for: '{sample_text_bg}'")
        ogg_audio_data = await tts_service.text_to_speech_ogg(
            text=sample_text_bg
        )

        if ogg_audio_data:
            output_dir = Path(__file__).parent.parent / 'tests' / 'temp'
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = output_dir / 'test_tts_output.ogg'

            try:
                with open(output_file_path, 'wb') as f:
                    f.write(ogg_audio_data)
                logger.info(
                    f'Successfully generated OGG audio and saved to: '
                    f'{output_file_path.resolve()}'
                )
                logger.info(f'File size: {len(ogg_audio_data)} bytes')
            except IOError as e:
                logger.error(f'Failed to write audio file: {e}')
        else:
            logger.error('Failed to generate OGG audio data.')

        logger.info('TTS service test finished.')

    asyncio.run(main_test())
