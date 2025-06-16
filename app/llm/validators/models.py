from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AttemptValidationResponse(BaseModel):
    is_correct: bool = Field(description='Whether the answer is correct')
    feedback: str = Field(
        description='If answer is correct, empty string. '
        'Else answer the question "What\'s wrong with this user '
        'answer?" '
        '- clearly shortly explain grammatical, spelling, '
        'syntactic, semantic or other errors.\n '
        "Warning! Feedback for the user must be in user's "
        'language.\n'
        'Be concise.',
    )
    error_tags: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description='A JSON object with keys "grammar" and "vocabulary", '
        'each containing a list of specific error topics '
        '(strings) '
        'if the answer is incorrect. Use ONLY tags from the '
        'provided lists. '
        'If correct or no specific tags apply, this can be null '
        'or empty lists.',
    )
