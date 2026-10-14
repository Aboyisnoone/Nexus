from datetime import datetime
from typing import Tuple, Optional
from pydantic import Field
from nexus.core.domain.base import FrozenBaseModel
from nexus.core.domain.calendar import CalendarEvent
from nexus.core.domain.memory import MemoryItem
from nexus.core.domain.scenario import Scenario
from nexus.core.decision.actions import AgentAction

class ActionRecord(FrozenBaseModel):
    action: AgentAction
    recorded_at: datetime
    status: str = "APPLIED"

class SimulationState(FrozenBaseModel):
    simulated_time: datetime
    calendar: Tuple[CalendarEvent, ...]
    memory: Tuple[MemoryItem, ...]
    action_history: Tuple[ActionRecord, ...] = Field(default_factory=tuple)
    
    @classmethod
    def from_scenario(cls, scenario: Scenario) -> "SimulationState":
        return cls(
            simulated_time=scenario.simulated_time,
            calendar=scenario.initial_state.calendar,
            memory=scenario.initial_state.memory,
            action_history=()
        )

class SimulationResult(FrozenBaseModel):
    status: str
    action_type: str | None
    state_before: SimulationState
    state_after: Optional[SimulationState] = None
    action_record: Optional[ActionRecord] = None
    error: Optional[str] = None
