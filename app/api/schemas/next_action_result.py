from datetime import timedelta
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.api.schemas.exercise import ExerciseSchema
from app.core.enums import UserAction


class NextActionSchema(BaseModel):
    exercise: Optional[ExerciseSchema] = None
    action: UserAction
    message: Optional[str] = None
    pause: Optional[timedelta] = None
    keyboard: Optional[List[Dict[str, str]]] = None
