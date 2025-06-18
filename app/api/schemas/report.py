from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserReportResponse(BaseModel):
    report_id: int
    user_id: int
    bot_id: str
    week_start_date: date
    short_report: str
    full_report: Optional[str] = None
    generated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ReportNotFound(BaseModel):
    detail: str = 'Report not found'
