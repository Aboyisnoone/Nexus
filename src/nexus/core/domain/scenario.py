from datetime import datetime
from typing import Tuple
from pydantic import Field, model_validator

from .calendar import CalendarEvent
from .memory import MemoryItem
from .event import Event
from .evaluation import Assertion
from .base import FrozenBaseModel

class InitialState(FrozenBaseModel):
    calendar: Tuple[CalendarEvent, ...] = Field(default_factory=tuple)
    memory: Tuple[MemoryItem, ...] = Field(default_factory=tuple)

class ExpectedEvaluation(FrozenBaseModel):
    assertions: Tuple[Assertion, ...] = Field(default_factory=tuple)

class Scenario(FrozenBaseModel):
    scenario_id: str
    description: str | None = None
    simulated_time: datetime
    initial_state: InitialState
    events: Tuple[Event, ...] = Field(default_factory=tuple)
    expected_evaluation: ExpectedEvaluation

    @model_validator(mode='after')
    def validate_scenario(self) -> 'Scenario':
        if self.simulated_time.tzinfo is None:
            raise ValueError("simulated_time must be timezone-aware")
        return self
