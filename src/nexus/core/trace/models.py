from enum import Enum
from typing import Tuple, Union, Annotated, Optional, Literal
from datetime import datetime
from pydantic import Field

from nexus.core.domain.base import FrozenBaseModel
from nexus.core.domain.memory import MemoryItem
from nexus.core.simulation.models import SimulationState, SimulationResult
from nexus.core.scheduling.models import CandidateSlot
from nexus.core.decision.actions import AgentAction
from nexus.core.decision.validator import ValidationResult
from nexus.core.evaluation.evaluator import EvaluationReport

class TraceStepType(str, Enum):
    STATE_BEFORE = "STATE_BEFORE"
    MEMORY = "MEMORY"
    VALID_OPTIONS = "VALID_OPTIONS"
    LLM_ACTION = "LLM_ACTION"
    VALIDATION = "VALIDATION"
    STATE_TRANSITION = "STATE_TRANSITION"
    STATE_AFTER = "STATE_AFTER"
    EVALUATION = "EVALUATION"
    FAILURE = "FAILURE"

class TraceStepBase(FrozenBaseModel):
    step_index: int
    step_type: TraceStepType
    simulated_time: datetime
    recorded_at: Optional[datetime] = None

class StateBeforeStep(TraceStepBase):
    step_type: Literal[TraceStepType.STATE_BEFORE] = TraceStepType.STATE_BEFORE
    state: SimulationState

class MemoryStep(TraceStepBase):
    step_type: Literal[TraceStepType.MEMORY] = TraceStepType.MEMORY
    retrieved_memory: Tuple[MemoryItem, ...]

class ValidOptionsStep(TraceStepBase):
    step_type: Literal[TraceStepType.VALID_OPTIONS] = TraceStepType.VALID_OPTIONS
    candidates: Tuple[CandidateSlot, ...]

class LlmActionStep(TraceStepBase):
    step_type: Literal[TraceStepType.LLM_ACTION] = TraceStepType.LLM_ACTION
    action: AgentAction

class ValidationStep(TraceStepBase):
    step_type: Literal[TraceStepType.VALIDATION] = TraceStepType.VALIDATION
    validation_result: ValidationResult

class StateTransitionStep(TraceStepBase):
    step_type: Literal[TraceStepType.STATE_TRANSITION] = TraceStepType.STATE_TRANSITION
    simulation_result: SimulationResult

class StateAfterStep(TraceStepBase):
    step_type: Literal[TraceStepType.STATE_AFTER] = TraceStepType.STATE_AFTER
    state: SimulationState

class EvaluationStep(TraceStepBase):
    step_type: Literal[TraceStepType.EVALUATION] = TraceStepType.EVALUATION
    report: EvaluationReport

class FailureStep(TraceStepBase):
    step_type: Literal[TraceStepType.FAILURE] = TraceStepType.FAILURE
    error_code: str
    detail: str

TraceStep = Annotated[
    Union[
        StateBeforeStep,
        MemoryStep,
        ValidOptionsStep,
        LlmActionStep,
        ValidationStep,
        StateTransitionStep,
        StateAfterStep,
        EvaluationStep,
        FailureStep
    ],
    Field(discriminator="step_type")
]

class TraceMetadata(FrozenBaseModel):
    trace_id: str
    scenario_id: str
    agent_version: str

class DecisionTrace(FrozenBaseModel):
    metadata: TraceMetadata
    steps: Tuple[TraceStep, ...]
