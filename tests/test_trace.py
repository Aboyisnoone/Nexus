import pytest
from datetime import datetime, timezone, timedelta
from nexus.core.trace import DecisionTraceBuilder, TraceMetadata
from nexus.core.scenario_loader import load_scenario
from nexus.core.simulation import SimulationState, apply_action
from nexus.core.decision import validate_and_wrap_action, PolicyContext
from nexus.core.evaluation import evaluate

@pytest.fixture
def simulated_time():
    return datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)

@pytest.fixture
def recorded_time():
    return datetime(2024, 11, 1, 9, 0, 5, tzinfo=timezone.utc)

@pytest.fixture
def metadata():
    return TraceMetadata(trace_id="t1", scenario_id="s1", agent_version="v1")

@pytest.fixture
def builder(metadata):
    return DecisionTraceBuilder(metadata)

def test_empty_builder_can_be_created(builder, metadata):
    assert builder._metadata == metadata
    assert builder._finalized is False

def test_valid_complete_trace(builder, simulated_time, recorded_time):
    from nexus.core.decision.actions import ProposeTimesAction, CommunicationTemplate
    from nexus.core.decision.validator import ValidationResult
    from nexus.core.simulation.models import SimulationResult
    from nexus.core.evaluation.evaluator import EvaluationReport, EvaluationStatus
    from nexus.core.scheduling.models import CandidateSlot
    from nexus.core.domain.memory import MemoryItem, MemoryState
    
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    from datetime import datetime, timezone
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    memory = (MemoryItem(id="m1", context_id="c1", key="k", value="v", state=MemoryState.CONFIRMED, simulated_time=sim_time, evidence=()),)
    options = (CandidateSlot(start=simulated_time, end=simulated_time + timedelta(hours=1), valid=True, violations=()),)
    
    # We construct raw objects just to test trace logic
    action = ProposeTimesAction(
        action_type="PROPOSE_TIMES",
        ranked_options=("slot_B", "slot_A"),
        selected_option="slot_B",
        communication={"template": "PROPOSE_SELECTED_SLOTS"}
    )
    val_res = ValidationResult(valid=True, errors=())
    sim_res = SimulationResult(status="APPLIED", action_type="PROPOSE_TIMES", state_before=state, state_after=state, action_record=None)
    eval_rep = EvaluationReport(status=EvaluationStatus.PASS, total=0, passed=0, failed=0, assertions=())
    
    builder.record_state_before(simulated_time, state, recorded_at=recorded_time)
    builder.record_memory(simulated_time, memory, recorded_at=recorded_time)
    builder.record_valid_options(simulated_time, options, recorded_at=recorded_time)
    builder.record_llm_action(simulated_time, action, recorded_at=recorded_time)
    builder.record_validation(simulated_time, val_res, recorded_at=recorded_time)
    builder.record_state_transition(simulated_time, sim_res, recorded_at=recorded_time)
    builder.record_state_after(simulated_time, state, recorded_at=recorded_time)
    builder.record_evaluation(simulated_time, eval_rep, recorded_at=recorded_time)
    
    trace = builder.finalize()
    assert len(trace.steps) == 8
    # check stable sequence order
    for i, step in enumerate(trace.steps):
        assert step.step_index == i + 1

def test_incorrect_payload_rejected(builder, simulated_time):
    # Pass a string instead of SimulationState
    with pytest.raises(Exception):
        builder.record_state_before(simulated_time, "wrong_type")
        builder.finalize() # Will fail pydantic validation if it somehow accepted it

def test_finalized_trace_immutable(builder, simulated_time):
    from nexus.core.simulation.models import SimulationState
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    builder.record_state_before(simulated_time, state)
    builder.record_failure(simulated_time, "TEST", "Fail")
    trace = builder.finalize()
    
    with pytest.raises(Exception):
        builder.record_memory(simulated_time, ())
        
    with pytest.raises(Exception):
        trace.metadata = "MUTATED"

def test_nested_snapshots_isolated(builder, simulated_time):
    # Create a list masquerading as a tuple to see if frozen conversion handles it?
    # Pydantic creates a deeply frozen tuple in SimulationState
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    builder.record_state_before(simulated_time, state)
    builder.record_failure(simulated_time, "TEST", "Fail")
    trace = builder.finalize()
    
    step = trace.steps[0]
    with pytest.raises(Exception):
        step.state.action_history = ("MUTATED",)

def test_invalid_sequence_rejected(builder, simulated_time):
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    builder.record_state_before(simulated_time, state)
    with pytest.raises(ValueError):
        # Cannot go from STATE_BEFORE straight to LLM_ACTION
        builder.record_llm_action(simulated_time, None)

def test_terminal_failure_represented(builder, simulated_time):
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    builder.record_state_before(simulated_time, state)
    builder.record_memory(simulated_time, ())
    builder.record_failure(simulated_time, "ERR_NO_VALID_OPTIONS", "No options available")
    
    trace = builder.finalize()
    assert len(trace.steps) == 3
    assert trace.steps[-1].step_type == "FAILURE"
    assert trace.steps[-1].error_code == "ERR_NO_VALID_OPTIONS"

def test_serialization(builder, simulated_time):
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    builder.record_state_before(simulated_time, state)
    builder.record_failure(simulated_time, "TEST", "Fail")
    trace = builder.finalize()
    
    json_data = trace.model_dump_json()
    assert "TEST" in json_data
    assert "STATE_BEFORE" in json_data

def test_determinism(metadata, simulated_time):
    state = SimulationState(simulated_time=simulated_time, calendar=(), memory=(), action_history=())
    
    b1 = DecisionTraceBuilder(metadata)
    b1.record_state_before(simulated_time, state)
    b1.record_failure(simulated_time, "A", "B")
    t1 = b1.finalize()
    
    b2 = DecisionTraceBuilder(metadata)
    b2.record_state_before(simulated_time, state)
    b2.record_failure(simulated_time, "A", "B")
    t2 = b2.finalize()
    
    assert t1 == t2

