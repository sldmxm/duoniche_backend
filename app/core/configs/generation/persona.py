from dataclasses import dataclass
from typing import Optional


@dataclass
class Persona:
    name: str
    role: str
    emotion: Optional[str] = None
    motivation: Optional[str] = None
    communication_style: Optional[str] = None
    voice_for_tts: Optional[str] = None
    emotion_instruction_for_tts: Optional[str] = None
