from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ReportStatus


class UserReport(BaseModel):
    """
    Represents a personalized weekly progress report for a user.
    """

    report_id: Optional[int] = Field(None, description='Internal report ID')
    user_id: int = Field(
        ...,
        description='ID of the user for whom the report is generated',
    )
    bot_id: str = Field(
        ...,
        description='Bot context (e.g., "Bulgarian") for the report.',
    )
    week_start_date: date = Field(
        ...,
        description='The start date of the week the report covers',
    )
    short_report: str = Field(
        ...,
        description='A concise, summary version of the report',
    )
    full_report: Optional[str] = Field(
        None,
        description='A detailed, comprehensive version of the report, '
        'which may be generated on-demand.',
    )
    status: ReportStatus = Field(
        default=ReportStatus.PENDING,
        description='The generation status of the detailed report.',
    )
    generated_at: datetime = Field(
        ...,
        description='Timestamp of when the report was generated',
    )
    model_config = ConfigDict(
        from_attributes=True,
    )
