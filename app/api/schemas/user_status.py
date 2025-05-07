from typing import Optional

from pydantic import BaseModel, Field


class UserBlockReportPayload(BaseModel):
    telegram_id: str = Field(..., description='Telegram ID')
    reason: Optional[str] = Field(
        default=None, description='Reason for blocking'
    )


class ReportBlockResponse(BaseModel):
    status: str = Field(..., description='Status of the report')
