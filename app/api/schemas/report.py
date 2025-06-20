from typing import Optional

from pydantic import BaseModel

from app.core.enums import ReportStatus


class DetailedReportResponse(BaseModel):
    current_report_status: Optional[ReportStatus] = None


class ReportNotFoundDetail(BaseModel):
    detail: str
