import pytest
from typing import Dict, Any
from unittest.mock import patch
from nexus.core.evaluation.regression import compare_evaluations, ComparisonStatus
from nexus.core.evaluation.suite import CoreSuiteRunner
from nexus.core.runner.pipeline import DecisionPipeline
from nexus.core.domain.scenario import Scenario
from nexus.core.evaluation.evaluator import EvaluationReport, EvaluationStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexus.core.persistence.models import Base, LlmRecordingModel
from nexus.core.persistence.repository import NexusRepository
from datetime import datetime, timezone
from nexus.core.domain.evaluation import ActionTypeEquals, NoCalendarOverlap
from nexus.core.decision.validator import ValidationResult, ValidationErrorDetail, ValidationErrorCode
from nexus.core.decision.actions import ProposeTimesAction, ActionType

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return NexusRepository(Session())

@pytest.fixture
def sample_scenario():
    return Scenario(
        scenario_id="happy_path_01",
        description="Simple test scenario",
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
                NoCalendarOverlap(type="no_calendar_overlap")
            ]
        }
    )

class FakeLLMClient:
    def __init__(self, response_template: Dict[str, Any]):
        self.response_template = response_template
        self.calls = 0
        
    def generate(self, prompt: Dict[str, Any]) -> tuple[Dict[str, Any], str]:
        self.calls += 1
        return self.response_template, "fake-model-1"

def test_offline_regression_integration(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    
    valid_response = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_0"],
        "selected_option": "slot_0",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"},
        "preference_basis": ["AFTERNOON_PREFERRED"]
    }
    llm_client = FakeLLMClient(valid_response)
    pipeline = DecisionPipeline(repo, llm_client)
    
    baseline_live_result = pipeline.run_live(sample_scenario, agent_version="v0.1")
    baseline_run_id = baseline_live_result.run_id
    
    runner = CoreSuiteRunner(repo, llm_client, "scenarios/core_10")
    
    baseline_replay_result = pipeline.run_replay(baseline_run_id, override_agent_version="v0.1")
    baseline_report = runner.evaluate_run(sample_scenario, baseline_replay_result)
    assert baseline_report.status == EvaluationStatus.PASS, f"Baseline failed: {baseline_report}"
    
    with patch("nexus.core.runner.pipeline.validate_action") as mock_validate:
        mock_action = ProposeTimesAction(**valid_response)
        mock_validate.return_value = (mock_action, ValidationResult(
            valid=False,
            errors=[ValidationErrorDetail(code=ValidationErrorCode.ERR_POLICY_VIOLATION, detail="Patched policy failure")]
        ))
        
        candidate_replay_result = pipeline.run_replay(baseline_run_id, override_agent_version="v0.2")
        candidate_report = runner.evaluate_run(sample_scenario, candidate_replay_result)
        
    assert candidate_report.status == EvaluationStatus.FAIL
    assert candidate_replay_result.simulation_result.status == "FAILED"
    
    comparison = compare_evaluations(
        scenario=sample_scenario,
        baseline_version="v0.1",
        candidate_version="v0.2",
        baseline_run_id=baseline_replay_result.run_id,
        candidate_run_id=candidate_replay_result.run_id,
        baseline_report=baseline_report,
        candidate_report=candidate_report,
        baseline_error=baseline_replay_result.simulation_result.error,
        candidate_error=candidate_replay_result.simulation_result.error
    )
    
    assert comparison.status == ComparisonStatus.REGRESSION
    assert comparison.baseline_status == "PASS"
    assert comparison.candidate_status == "FAIL"
    assert comparison.candidate_failure_code == "ERR_POLICY_VIOLATION"
    assert len(comparison.changed_assertions) > 0
    assert comparison.changed_assertions[0].baseline_passed is True
    assert comparison.changed_assertions[0].candidate_passed is False

def test_incompatible_input_regression(repo, sample_scenario):
    repo.save_scenario(sample_scenario)
    
    valid_response = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_0"],
        "selected_option": "slot_0",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"},
        "preference_basis": ["AFTERNOON_PREFERRED"]
    }
    llm_client = FakeLLMClient(valid_response)
    pipeline = DecisionPipeline(repo, llm_client)
    
    baseline_live_result = pipeline.run_live(sample_scenario, agent_version="v0.1")
    baseline_run_id = baseline_live_result.run_id
    
    runner = CoreSuiteRunner(repo, llm_client, "scenarios/core_10")
    baseline_replay_result = pipeline.run_replay(baseline_run_id, override_agent_version="v0.1")
    baseline_report = runner.evaluate_run(sample_scenario, baseline_replay_result)
    
    model = repo.session.query(LlmRecordingModel).filter_by(run_id=baseline_run_id, call_index=0).first()
    model.prompt_hash = "mismatched_hash"
    repo.session.commit()
    
    candidate_replay_result = pipeline.run_replay(baseline_run_id, override_agent_version="v0.2")
    candidate_report = runner.evaluate_run(sample_scenario, candidate_replay_result)
    
    comparison = compare_evaluations(
        scenario=sample_scenario,
        baseline_version="v0.1",
        candidate_version="v0.2",
        baseline_run_id=baseline_replay_result.run_id,
        candidate_run_id=candidate_replay_result.run_id,
        baseline_report=baseline_report,
        candidate_report=candidate_report,
        baseline_error=baseline_replay_result.simulation_result.error,
        candidate_error=candidate_replay_result.simulation_result.error
    )
    
    assert comparison.status == ComparisonStatus.INCOMPATIBLE_INPUT
    assert comparison.candidate_failure_code == "ERR_REPLAY_INPUT_MISMATCH"
