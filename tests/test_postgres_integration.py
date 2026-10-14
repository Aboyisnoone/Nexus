import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from nexus.core.persistence.models import Base, JSON_TYPE
from nexus.core.persistence.repository import NexusRepository

from nexus.core.domain.scenario import Scenario
from nexus.core.domain.memory import MemoryItem, MemoryState
from nexus.core.trace.builder import DecisionTraceBuilder
from nexus.core.trace.models import TraceMetadata
from nexus.core.simulation.models import SimulationState
from nexus.core.scenario_loader import load_scenario

PG_URL = os.environ.get("NEXUS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not PG_URL, reason="NEXUS_TEST_DATABASE_URL not set")

@pytest.fixture
def engine():
    engine = create_engine(PG_URL)
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
    return load_scenario("scenarios/examples/happy_path.yaml")

def test_pg_schema_is_jsonb(engine):
    # Verify that the columns are actually JSONB in PostgreSQL
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'decision_traces' AND column_name = 'trace_data_json';"
        )).scalar()
        assert result == "jsonb", f"Expected jsonb, got {result}"

def test_pg_decision_trace_persistence(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    run_id = "pg_run_1"
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
    builder.record_failure(simulated_time=sim_time, error_code="ERR_PG", detail="PG test failure")
    
    trace = builder.finalize()
    repo.save_decision_trace(trace)
    
    loaded_trace = repo.load_decision_trace(run_id)
    assert loaded_trace is not None
    assert loaded_trace.metadata.trace_id == run_id
    assert len(loaded_trace.steps) == 2
    assert loaded_trace.steps[1].error_code == "ERR_PG"

def test_pg_duplicate_llm_recording_fails(repo, sample_scenario):
    import sqlalchemy.exc
    
    repo.save_scenario(sample_scenario)
    repo.save_run(
        run_id="pg_run_2",
        scenario_id=sample_scenario.scenario_id,
        agent_version="v0.1",
        mode="LIVE",
        status="IN_PROGRESS"
    )
    
    prompt = {"test": 1}
    response = {"test": 2}
    
    repo.save_llm_recording(
        run_id="pg_run_2",
        call_index=0,
        prompt_hash="hash1",
        prompt_json=prompt,
        response_json=response
    )
    
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        repo.save_llm_recording(
            run_id="pg_run_2",
            call_index=0,
            prompt_hash="hash2",
            prompt_json=prompt,
            response_json=response
        )
