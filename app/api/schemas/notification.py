from pydantic import BaseModel


class RelevanceCheckResponse(BaseModel):
    is_relevant: bool
