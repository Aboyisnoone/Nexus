from sqlalchemy import text
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from nexus.api.main import app
from nexus.api.dependencies import get_db, get_llm_client
from nexus.core.persistence.models import Base
from nexus.core.domain.scenario import Scenario
from nexus.core.domain.evaluation import ActionTypeEquals, NoCalendarOverlap
from nexus.core.decision.actions import ProposeTimesAction
from datetime import datetime, timezone
from typing import Dict, Any

# Setup in-memory sqlite with StaticPool to share connection
engine = create_engine(
    "sqlite:///:memory:", 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

class FakeAPI_LLMClient:
    def __init__(self, response_template: Dict[str, Any]):
        self.response_template = response_template
        self.calls = 0
        
    def generate(self, prompt: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        self.calls += 1
        return self.response_template, "fake-model-1"

fake_llm = FakeAPI_LLMClient({
    "action_type": "PROPOSE_TIMES",
    "ranked_options": ["slot_0"],
    "selected_option": "slot_0",
    "communication": {"template": "PROPOSE_SELECTED_SLOTS"},
    "preference_basis": ["AFTERNOON_PREFERRED"]
})

def override_get_llm_client():
    return fake_llm

app.dependency_overrides[get_llm_client] = override_get_llm_client

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Setup fresh scenario for API
    db = SessionLocal()
    from nexus.core.persistence.repository import NexusRepository
    repo = NexusRepository(db)
    scenario = Scenario(
        scenario_id="api_test_scenario",
        description="Simple test scenario for API",
        simulated_time=datetime(2024, 11, 1, 9, 0, 0, tzinfo=timezone.utc),
        initial_state={"calendar": [], "memory": []},
        events=[
            {
                "actor": "client",
                "intent": "request_meeting",
                "payload": {
                    "scheduling_constraints": {
                        "window_start": "2024-11-01T10:00:00Z",
                        "window_end": "2024-11-01T12:00:00Z",
                        "duration": "PT1H",
                        "granularity": "PT30M"
                    }
                }
            }
        ],
        expected_evaluation={
            "assertions": [
                ActionTypeEquals(type="action_type_equals", expected="PROPOSE_TIMES"),
            ]
        }
    )
    repo.save_scenario(scenario)
    db.close()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus"}

def test_live_run():
    response = client.post("/api/v1/scenarios/api_test_scenario/run?mode=LIVE&agent_version=v0.1")
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_id"] == "api_test_scenario"
    assert data["mode"] == "LIVE"
    assert data["status"] == "APPLIED"
    assert "run_id" in data
    assert data["evaluation"]["status"] == "PASS"

def test_live_run_scenario_not_found():
    response = client.post("/api/v1/scenarios/unknown/run?mode=LIVE")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "SCENARIO_NOT_FOUND"

def test_replay_run():
    # 1. First run LIVE
    live_resp = client.post("/api/v1/scenarios/api_test_scenario/run?mode=LIVE&agent_version=v0.1")
    run_id = live_resp.json()["run_id"]
    
    # 2. Replay
    replay_resp = client.post(f"/api/v1/scenarios/api_test_scenario/run?mode=REPLAY&replay_of={run_id}&agent_version=v0.1")
    assert replay_resp.status_code == 200
    data = replay_resp.json()
    assert data["mode"] == "REPLAY"
    assert data["status"] == "APPLIED"

def test_replay_missing_source():
    response = client.post("/api/v1/scenarios/api_test_scenario/run?mode=REPLAY")
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "MISSING_REPLAY_SOURCE"

def test_get_trace():
    live_resp = client.post("/api/v1/scenarios/api_test_scenario/run?mode=LIVE&agent_version=v0.1")
    run_id = live_resp.json()["run_id"]
    
    trace_resp = client.get(f"/api/v1/runs/{run_id}/trace")
    assert trace_resp.status_code == 200
    data = trace_resp.json()
    assert "trace" in data
    assert "steps" in data["trace"]

def test_get_trace_not_found():
    trace_resp = client.get("/api/v1/runs/unknown_run/trace")
    assert trace_resp.status_code == 404
    data = trace_resp.json()
    assert data["error"]["code"] == "TRACE_NOT_FOUND"

def test_get_memory():
    mem_resp = client.get("/api/v1/memory/some_context")
    assert mem_resp.status_code == 200
    assert mem_resp.json() == {"memories": []}




def test_trace_modification_cannot_alter_evaluation(setup_db):
    from tests.test_api import client
    
    # Run live
    live_resp = client.post("/api/v1/scenarios/api_test_scenario/run?mode=LIVE&agent_version=v0.1")
    run_id = live_resp.json()["run_id"]
    
    # Let's deliberately modify the trace in the DB to break it
    from tests.test_api import SessionLocal
    db = SessionLocal()
    from nexus.core.persistence.repository import NexusRepository
    repo = NexusRepository(db)
    
    trace = repo.load_decision_trace(run_id)
    db.execute(text("UPDATE decision_traces SET trace_data_json = '{}' WHERE step_name = 'VALID_OPTIONS' AND run_id = :run_id"), {"run_id": run_id})
    db.commit()
    db.close()
    
    # Run Replay
    replay_resp = client.post(f"/api/v1/scenarios/api_test_scenario/run?mode=REPLAY&replay_of={run_id}&agent_version=v0.1")
    assert replay_resp.status_code == 200
    data = replay_resp.json()
    assert data["evaluation"]["status"] == "PASS" # Because replay evaluates the ACTUAL candidate_dict, not the trace!



