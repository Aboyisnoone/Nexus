from enum import Enum
from datetime import datetime
from pydantic import ConfigDict, model_validator
from .base import FrozenBaseModel

class Visibility(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

class CalendarEvent(FrozenBaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    visibility: Visibility
    priority: str | None = None

    @model_validator(mode='after')
    def validate_event(self) -> 'CalendarEvent':
        if self.start >= self.end:
            raise ValueError("start time must be before end time")
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("start and end times must be timezone-aware")
        return self
