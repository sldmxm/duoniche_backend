import logging
from typing import Optional

import aioboto3
from botocore.exceptions import (
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from app.config import settings

logger = logging.getLogger(__name__)


class R2FileStorageService:
    def __init__(
        self,
        account_id: str = settings.cloudflare_r2_account_id,
        access_key_id: str = settings.cloudflare_r2_access_key_id,
        secret_access_key: str = settings.cloudflare_r2_secret_access_key,
        bucket_name: str = settings.cloudflare_r2_bucket_name,
        public_url_prefix: str = settings.cloudflare_r2_public_url_prefix,
    ):
        if not all(
            [
                account_id,
                access_key_id,
                secret_access_key,
                bucket_name,
                public_url_prefix,
            ]
        ):
            error_msg = (
                'Cloudflare R2 credentials or bucket_name/public_url_prefix '
                'are not fully configured.'
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.endpoint_url = f'https://{account_id}.r2.cloudflarestorage.com'
        self.bucket_name = bucket_name
        self.public_url_prefix = public_url_prefix.rstrip('/')
        self.session = aioboto3.Session()
        logger.info(
            f'R2FileStorageService (aioboto3) session configured for bucket: '
            f'{self.bucket_name}'
        )

    async def upload_audio(
        self,
        file_data: bytes,
        file_name: str,
        content_type: str = 'audio/ogg',
    ) -> Optional[str]:
        """
        Uploads audio data to Cloudflare R2 using aioboto3
        and returns the public URL.
        """
        try:
            async with self.session.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=settings.cloudflare_r2_access_key_id,
                aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
                region_name='auto',
            ) as s3_client:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=content_type,
                )
            public_url = f'{self.public_url_prefix}/{file_name}'
            logger.info(
                f'Successfully uploaded {file_name} to R2. URL: {public_url}'
            )
            return public_url
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(
                f'Credentials error during R2 S3 client operation: {e}'
            )
            return None
        except ClientError as e:
            logger.error(f'Failed to upload {file_name} to R2: {e}')
            return None
        except Exception as e:
            logger.error(
                f'An unexpected error occurred during R2 upload '
                f'of {file_name}: {e}',
                exc_info=True,
            )
            return None
