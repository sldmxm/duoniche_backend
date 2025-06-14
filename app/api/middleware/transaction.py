import logging

from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response

from app.db.db import async_session_maker

logger = logging.getLogger(__name__)


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        async with async_session_maker() as session:
            request.state.db = session
            try:
                response = await call_next(request)
                await session.commit()
            except Exception:
                logger.exception(
                    'An error occurred during a database transaction, '
                    'rolling back.'
                )
                await session.rollback()
                raise
        return response
