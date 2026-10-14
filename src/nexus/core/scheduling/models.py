from datetime import datetime, timedelta, time
from typing import Tuple
from pydantic import Field, model_validator
from nexus.core.domain.base import FrozenBaseModel
from nexus.core.time import _require_aware
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class WorkingWindow(FrozenBaseModel):
    timezone: str
    start_local: time
    end_local: time
    
    @model_validator(mode='after')
    def validate_working_window(self):
        if self.start_local >= self.end_local:
            raise ValueError("ERR_INVALID_WORKING_WINDOW: Working window start must be before end")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError(f"ERR_INVALID_TIMEZONE: {self.timezone}")
        return self

class SchedulingConstraints(FrozenBaseModel):
    window_start: datetime
    window_end: datetime
    duration: timedelta
    granularity: timedelta
    buffer_before: timedelta = Field(default_factory=timedelta)
    buffer_after: timedelta = Field(default_factory=timedelta)
    working_window: WorkingWindow | None = None

    @model_validator(mode='after')
    def validate_constraints(self):
        _require_aware(self.window_start)
        _require_aware(self.window_end)
        if self.window_start >= self.window_end:
            raise ValueError("ERR_INVALID_WINDOW: window_start must be before window_end")
        if self.duration.total_seconds() <= 0:
            raise ValueError("ERR_INVALID_DURATION: duration must be positive")
        if self.granularity.total_seconds() <= 0:
            raise ValueError("ERR_INVALID_GRANULARITY: granularity must be positive")
        if self.duration > (self.window_end - self.window_start):
            raise ValueError("ERR_INVALID_DURATION: duration exceeds scheduling window")
        return self

class CandidateSlot(FrozenBaseModel):
    start: datetime
    end: datetime
    valid: bool
    violations: Tuple[str, ...] = Field(default_factory=tuple)
