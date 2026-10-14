from typing import List, Optional
from datetime import datetime

from .models import (
    TraceMetadata,
    DecisionTrace,
    TraceStep,
    TraceStepType,
    StateBeforeStep,
    MemoryStep,
    ValidOptionsStep,
    LlmActionStep,
    ValidationStep,
    StateTransitionStep,
    StateAfterStep,
    EvaluationStep,
    FailureStep,
)

_EXPECTED_TRANSITIONS = {
    TraceStepType.STATE_BEFORE: [TraceStepType.MEMORY, TraceStepType.FAILURE],
    TraceStepType.MEMORY: [TraceStepType.VALID_OPTIONS, TraceStepType.FAILURE],
    TraceStepType.VALID_OPTIONS: [TraceStepType.LLM_ACTION, TraceStepType.FAILURE],
    TraceStepType.LLM_ACTION: [TraceStepType.VALIDATION, TraceStepType.FAILURE],
    TraceStepType.VALIDATION: [TraceStepType.STATE_TRANSITION, TraceStepType.FAILURE],
    TraceStepType.STATE_TRANSITION: [TraceStepType.STATE_AFTER, TraceStepType.FAILURE],
    TraceStepType.STATE_AFTER: [TraceStepType.EVALUATION, TraceStepType.FAILURE],
    TraceStepType.EVALUATION: [],
    TraceStepType.FAILURE: []
}

class DecisionTraceBuilder:
    def __init__(self, metadata: TraceMetadata):
        self._metadata = metadata
        self._steps: List[TraceStep] = []
        self._next_index = 1
        self._finalized = False
        self._last_step_type = None

    def _check_finalized(self):
        if self._finalized:
            raise RuntimeError("DecisionTrace is finalized and cannot be modified.")
            
    def _validate_transition(self, next_step: TraceStepType):
        if self._last_step_type is None:
            if next_step != TraceStepType.STATE_BEFORE:
                raise ValueError(f"Trace must begin with {TraceStepType.STATE_BEFORE}, got {next_step}")
        else:
            allowed = _EXPECTED_TRANSITIONS[self._last_step_type]
            if next_step not in allowed:
                raise ValueError(f"Invalid step transition from {self._last_step_type} to {next_step}")
                
        self._last_step_type = next_step

    def record_state_before(self, simulated_time: datetime, state, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.STATE_BEFORE)
        step = StateBeforeStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            state=state
        )
        self._steps.append(step)
        self._next_index += 1

    def record_memory(self, simulated_time: datetime, retrieved_memory, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.MEMORY)
        step = MemoryStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            retrieved_memory=tuple(retrieved_memory)
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_valid_options(self, simulated_time: datetime, candidates, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.VALID_OPTIONS)
        step = ValidOptionsStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            candidates=tuple(candidates)
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_llm_action(self, simulated_time: datetime, action, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.LLM_ACTION)
        step = LlmActionStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            action=action
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_validation(self, simulated_time: datetime, validation_result, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.VALIDATION)
        step = ValidationStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            validation_result=validation_result
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_state_transition(self, simulated_time: datetime, simulation_result, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.STATE_TRANSITION)
        step = StateTransitionStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            simulation_result=simulation_result
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_state_after(self, simulated_time: datetime, state, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.STATE_AFTER)
        step = StateAfterStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            state=state
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_evaluation(self, simulated_time: datetime, report, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.EVALUATION)
        step = EvaluationStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            report=report
        )
        self._steps.append(step)
        self._next_index += 1
        
    def record_failure(self, simulated_time: datetime, error_code: str, detail: str, recorded_at: Optional[datetime] = None):
        self._check_finalized()
        self._validate_transition(TraceStepType.FAILURE)
        step = FailureStep(
            step_index=self._next_index,
            simulated_time=simulated_time,
            recorded_at=recorded_at,
            error_code=error_code,
            detail=detail
        )
        self._steps.append(step)
        self._next_index += 1
        
    def finalize(self) -> DecisionTrace:
        self._check_finalized()
        self._finalized = True
        return DecisionTrace(
            metadata=self._metadata,
            steps=tuple(self._steps)
        )
