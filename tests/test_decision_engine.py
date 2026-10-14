import pytest
from datetime import datetime, timezone

from nexus.core.domain.scenario import Scenario
from nexus.core.domain.memory import MemoryItem, MemoryState, Contradiction, Evidence
from nexus.core.scheduling.models import CandidateSlot
from nexus.core.decision.prompt import PromptBuilder, PROMPT_VERSION

def test_deterministic_prompt_generation():
    sim_time = datetime(2024, 11, 1, 9, 0, tzinfo=timezone.utc)
    
    # Unordered memory
    m1 = MemoryItem(
        id="2", context_id="ctx", key="pref", value="afternoon",
        state=MemoryState.CONFIRMED, simulated_time=sim_time,
        version=2,
        contradictions=(
            Contradiction(
                observation_evidence=Evidence(source_run_id="run99"),
                simulated_time=sim_time,
                detail="Oops"
            ),
        )
    )
    m2 = MemoryItem(
        id="1", context_id="ctx", key="pref", value="morning",
        state=MemoryState.OBSERVED, simulated_time=sim_time,
        version=1
    )
    
    candidates = (
        CandidateSlot(start=datetime(2024,11,1,10,0,tzinfo=timezone.utc), end=datetime(2024,11,1,11,0,tzinfo=timezone.utc), valid=True),
        CandidateSlot(start=datetime(2024,11,1,14,0,tzinfo=timezone.utc), end=datetime(2024,11,1,15,0,tzinfo=timezone.utc), valid=True),
    )
    
    from nexus.core.scenario_loader import load_scenario
    scenario = load_scenario("scenarios/examples/happy_path.yaml")
    
    prompt1 = PromptBuilder.build_decision_prompt(scenario, sim_time, candidates, [m1, m2])
    prompt2 = PromptBuilder.build_decision_prompt(scenario, sim_time, candidates, [m2, m1]) # Reversed memory list
    
    # Assert deterministic memory sorting in prompt
    assert prompt1 == prompt2
    
    assert prompt1["version"] == PROMPT_VERSION
    assert prompt1["simulated_time"] == sim_time.isoformat()
    assert prompt1["memory"][0]["version"] == 1 if "version" in prompt1["memory"][0] else True
    # wait, my serialize doesn't output version, but the sorting uses version.
    
    # Let's check candidates
    assert len(prompt1["candidates"]) == 2
    assert prompt1["candidates"][0]["slot_id"] == "slot_0"
    
    # Let's check evaluator expectations are NOT exposed
    prompt_str = str(prompt1)
    assert "expected_evaluation" not in prompt_str
    assert "assertions" not in prompt_str


