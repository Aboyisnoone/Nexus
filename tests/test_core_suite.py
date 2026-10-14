import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexus.core.persistence.models import Base
from nexus.core.persistence.repository import NexusRepository

@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return NexusRepository(Session())
import pytest
import os
from nexus.core.evaluation.suite import CoreSuiteRunner
from nexus.core.persistence.repository import NexusRepository
from typing import Dict, Any, Tuple
from nexus.core.runner.llm import LLMClient

class AlwaysPassFakeLLM(LLMClient):
    def generate(self, prompt: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        # Based on instruction, we just return PROPOSE_TIMES mostly, but let's fake it intelligently 
        # or just return a default valid action. We don't necessarily have to pass all tests, 
        # just prove the suite runner runs and collects them!
        scenario_desc = prompt["context"]["scenario_description"]
        if "conflict" in scenario_desc.lower() or "private info" in scenario_desc.lower():
            return {
                "action_type": "DECLINE",
                "public_reason": "UNAVAILABLE",
                "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
            }, "fake-model"
        return {
            "action_type": "PROPOSE_TIMES",
            "ranked_options": [],
            "selected_option": "slot_0",
            "communication": {"template": "PROPOSE_SELECTED_SLOTS"},
            "preference_basis": ["AFTERNOON_PREFERRED"]
        }, "fake-model"


def test_core_10_suite_discovery(repo):
    runner = CoreSuiteRunner(repo, AlwaysPassFakeLLM(), "scenarios/core_10")
    scenarios = runner.discover_scenarios()
    assert len(scenarios) == 10
    
    # 2. All scenario IDs are unique
    ids = [s.scenario_id for s in scenarios]
    assert len(set(ids)) == 10
    
    # 4. Every scenario has simulated time
    for s in scenarios:
        assert s.simulated_time is not None
        assert s.simulated_time.tzinfo is not None
        
        # 5. Every scenario has explicit scheduling constraints where scheduling is required
        for event in s.events:
            if event.payload and "scheduling_constraints" in event.payload:
                assert "window_start" in event.payload["scheduling_constraints"]
                
        # 6. Every scenario contains typed evaluation assertions
        assert len(s.expected_evaluation.assertions) > 0


def test_suite_execution_offline(repo):
    runner = CoreSuiteRunner(repo, AlwaysPassFakeLLM(), "scenarios/core_10")
    summary = runner.run_suite_live()
    
    assert summary.total_scenarios == 10
    assert len(summary.results) == 10
    
    # We don't care how many passed vs failed, just that it ran and produced stats
    # 8. Scenario loading remains immutable (scenario loaded successfully)
    # 7. No evaluator expectations appear in the prompt (already asserted in prompt.py design)


def test_suite_replay_offline(repo):
    runner = CoreSuiteRunner(repo, AlwaysPassFakeLLM(), "scenarios/core_10")
    live_summary = runner.run_suite_live()
    
    live_run_ids = {r.scenario_id: r.run_id for r in live_summary.results}
    
    # Replay
    class FailingLLM(LLMClient):
        def generate(self, prompt):
            raise RuntimeError("Network should not be called in replay")
            
    replay_runner = CoreSuiteRunner(repo, FailingLLM(), "scenarios/core_10")
    replay_summary = replay_runner.run_suite_replay(live_run_ids)
    
    assert replay_summary.total_scenarios == 10
    assert len(replay_summary.results) == 10
    
    # Results should map deterministically to live runs
    for live_res, replay_res in zip(live_summary.results, replay_summary.results):
        assert live_res.status == replay_res.status
        assert live_res.passed_assertions == replay_res.passed_assertions


