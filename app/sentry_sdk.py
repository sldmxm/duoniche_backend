import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.langchain import LangchainIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.config import settings


def sentry_init():
    if settings.sentry_sdk:
        sentry_sdk.init(
            dsn=settings.sentry_sdk,
            integrations=[
                LoggingIntegration(),
                FastApiIntegration(),
                LangchainIntegration(),
                HttpxIntegration(),
                AsyncioIntegration(),
            ],
            traces_sample_rate=0.5,
            environment='production',
            send_default_pii=True,
        )
