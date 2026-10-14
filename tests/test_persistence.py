import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from nexus.core.persistence.models import Base
from nexus.core.persistence.repository import NexusRepository

from nexus.core.domain.scenario import Scenario
from nexus.core.domain.memory import MemoryItem, MemoryState
from nexus.core.trace.builder import DecisionTraceBuilder
from nexus.core.trace.models import TraceMetadata
from nexus.core.simulation.models import SimulationState
from nexus.core.scenario_loader import load_scenario

# This file contains pure domain serialization tests using SQLite in-memory database.
# As per architecture docs, this proves serialization boundaries but actual 
# PostgreSQL behavior is tested in test_postgres_integration.py.
TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def repo(session):
    return NexusRepository(session)

@pytest.fixture
def sample_scenario():
    # Load from happy_path.yaml
    return load_scenario("scenarios/examples/happy_path.yaml")

def test_scenario_persistence(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    
    loaded = repo.load_scenario(sample_scenario.scenario_id)
    assert loaded is not None
    assert loaded.scenario_id == sample_scenario.scenario_id
    assert loaded.simulated_time == sample_scenario.simulated_time
    assert len(loaded.expected_evaluation.assertions) == len(sample_scenario.expected_evaluation.assertions)

def test_run_persistence(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    
    repo.save_run(
        run_id="run_1",
        scenario_id=sample_scenario.scenario_id,
        agent_version="v0.1",
        mode="LIVE",
        status="COMPLETED",
        metrics={"total_time": 1.5}
    )
    
    run = repo.get_run("run_1")
    assert run is not None
    assert run.id == "run_1"
    assert run.mode == "LIVE"
    assert run.metrics_json["total_time"] == 1.5

def test_memory_persistence(repo):
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    mem = MemoryItem(
        id="mem_123",
        context_id="ctx_1",
        key="preference",
        value="morning",
        state=MemoryState.CONFIRMED,
        simulated_time=sim_time,
        evidence=()
    )
    repo.save_memory(mem)
    
    loaded = repo.load_memories("ctx_1")
    assert len(loaded) == 1
    assert loaded[0].id == "mem_123"
    assert loaded[0].key == "preference"
    assert loaded[0].state == MemoryState.CONFIRMED
    assert loaded[0].evidence == ()

def test_llm_recording_persistence(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    repo.save_run(
        run_id="run_2",
        scenario_id=sample_scenario.scenario_id,
        agent_version="v0.1",
        mode="LIVE",
        status="IN_PROGRESS"
    )
    
    prompt = {"messages": [{"role": "user", "content": "hello"}]}
    response = {"content": "world"}
    
    repo.save_llm_recording(
        run_id="run_2",
        call_index=0,
        prompt_hash="hash123",
        prompt_json=prompt,
        response_json=response
    )
    
    rec = repo.load_llm_recording("run_2", 0)
    assert rec is not None
    assert rec["prompt_hash"] == "hash123"
    assert rec["prompt_json"] == prompt
    assert rec["response_json"] == response

def test_decision_trace_persistence(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    run_id = "run_3"
    repo.save_run(
        run_id=run_id,
        scenario_id=sample_scenario.scenario_id,
        agent_version="v0.1",
        mode="LIVE",
        status="IN_PROGRESS"
    )
    
    metadata = TraceMetadata(trace_id=run_id, scenario_id=sample_scenario.scenario_id, agent_version="v0.1")
    builder = DecisionTraceBuilder(metadata)
    
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    state = SimulationState(simulated_time=sim_time, calendar=(), memory=(), action_history=())
    
    builder.record_state_before(simulated_time=sim_time, state=state)
    builder.record_failure(simulated_time=sim_time, error_code="ERR_TEST", detail="Test failure")
    
    trace = builder.finalize()
    repo.save_decision_trace(trace)
    
    loaded_trace = repo.load_decision_trace(run_id)
    assert loaded_trace is not None
    assert loaded_trace.metadata.trace_id == run_id
    assert len(loaded_trace.steps) == 2
    
    assert loaded_trace.steps[0].step_type == "STATE_BEFORE"
    assert loaded_trace.steps[1].step_type == "FAILURE"
    assert loaded_trace.steps[1].error_code == "ERR_TEST"

def test_malformed_json_fails_validation():
    from pydantic import ValidationError
    from nexus.core.trace.models import TraceStep
    from pydantic import TypeAdapter
    
    bad_payload = {
        "step_type": "STATE_BEFORE",
        "step_index": 1,
        "simulated_time": "2024-11-01T09:00:00Z"
        # missing 'state' field which is required for STATE_BEFORE
    }
    
    adapter = TypeAdapter(TraceStep)
    with pytest.raises(ValidationError):
        adapter.validate_python(bad_payload)
def test_duplicate_llm_recording_fails(repo, sample_scenario):
    import sqlalchemy.exc
    
    repo.save_scenario(sample_scenario)
    repo.save_run(
        run_id="run_4",
        scenario_id=sample_scenario.scenario_id,
        agent_version="v0.1",
        mode="LIVE",
        status="IN_PROGRESS"
    )
    
    prompt = {}
    response = {}
    
    repo.save_llm_recording(
        run_id="run_4",
        call_index=0,
        prompt_hash="hash123",
        prompt_json=prompt,
        response_json=response
    )
    
    # Save same run_id and call_index
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        repo.save_llm_recording(
            run_id="run_4",
            call_index=0,
            prompt_hash="hash456",
            prompt_json=prompt,
            response_json=response
        )

