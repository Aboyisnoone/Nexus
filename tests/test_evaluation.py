import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from nexus.core.domain.scenario import Scenario
from nexus.core.domain.evaluation import (
    ActionTypeEquals,
    SelectedOptionEquals,
    RankedOptionsEquals,
    PublicReasonEquals,
    CommunicationTemplateEquals,
    NoCalendarOverlap,
    CalendarUnchanged
)
from nexus.core.simulation import SimulationState, apply_action, SimulationResult, ActionRecord
from nexus.core.decision import validate_and_wrap_action, PolicyContext, ActionType, ProposeTimesAction, DeclineAction
from nexus.core.evaluation import evaluate, EvaluationStatus
from nexus.core.scheduling import CandidateSlot
from nexus.core.scenario_loader import load_scenario

@pytest.fixture
def base_scenario():
    # We will build assertions dynamically for tests, but start with a clean loaded scenario
    s = load_scenario("scenarios/examples/happy_path.yaml")
    return s

@pytest.fixture
def policy_ctx():
    return PolicyContext(
        valid_candidate_ids=("slot_A", "slot_B", "slot_C"),
        authorized_templates=("PROPOSE_SELECTED_SLOTS", "UNAVAILABLE_PROPOSE_ALTERNATIVES"),
        authorized_public_reasons=("UNAVAILABLE",)
    )

@pytest.fixture
def candidate_slots():
    dt_base = datetime(2024, 11, 1, 10, 0, tzinfo=timezone.utc)
    return {
        "slot_A": CandidateSlot(start=dt_base, end=dt_base + timedelta(minutes=30), valid=True, violations=()),
        "slot_B": CandidateSlot(start=dt_base + timedelta(hours=2), end=dt_base + timedelta(hours=2, minutes=30), valid=True, violations=()),
    }

def get_propose_action(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_B", "slot_A"],
        "selected_option": "slot_B",
        "preference_basis": ["AFTERNOON_PREFERRED"],
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    action, _ = validate_and_wrap_action(raw, policy_ctx)
    return action

def get_decline_action(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "preference_basis": ["PRIVATE_CONFLICT"],
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    action, _ = validate_and_wrap_action(raw, policy_ctx)
    return action

def mutate_scenario_assertions(scenario, assertions_tuple):
    # Helper to mutate scenario for testing
    from pydantic import BaseModel
    object.__setattr__(scenario.expected_evaluation, "assertions", assertions_tuple)

def test_all_passing_produces_pass(base_scenario, policy_ctx, candidate_slots):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (
        ActionTypeEquals(expected="PROPOSE_TIMES"),
        SelectedOptionEquals(expected="slot_B"),
        RankedOptionsEquals(expected=("slot_B", "slot_A")),
        CommunicationTemplateEquals(expected="PROPOSE_SELECTED_SLOTS"),
        CalendarUnchanged(),
        NoCalendarOverlap()
    ))
    
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.PASS
    assert report.passed == 6
    assert report.failed == 0

def test_one_failed_produces_fail(base_scenario, policy_ctx, candidate_slots):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (
        ActionTypeEquals(expected="PROPOSE_TIMES"),
        SelectedOptionEquals(expected="slot_A"), # FAILS
    ))
    
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.FAIL
    assert report.passed == 1
    assert report.failed == 1
    assert report.assertions[1].passed is False
    assert report.assertions[1].actual == "slot_B"

def test_action_type_equals(base_scenario, policy_ctx, candidate_slots):
    action = get_decline_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (ActionTypeEquals(expected="DECLINE"),))
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.PASS
    
    mutate_scenario_assertions(base_scenario, (ActionTypeEquals(expected="PROPOSE_TIMES"),))
    report2 = evaluate(base_scenario, sim_result, candidate_slots)
    assert report2.status == EvaluationStatus.FAIL
    assert report2.assertions[0].actual == "DECLINE"

def test_public_reason_equals(base_scenario, policy_ctx, candidate_slots):
    action = get_decline_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (PublicReasonEquals(expected="UNAVAILABLE"),))
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.PASS

def test_no_calendar_overlap_fails_if_overlap(base_scenario, policy_ctx, candidate_slots):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    # Event 1 is 10:00 to 11:00 UTC
    # slot_A is 10:00 to 10:30 UTC -> overlaps exactly!
    # slot_B is 12:00 to 12:30 UTC -> no overlap
    
    # Let's test with slot_B (selected option)
    mutate_scenario_assertions(base_scenario, (NoCalendarOverlap(),))
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.PASS
    
    # Now let's change selected_option to slot_A to simulate an overlap
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_A"],
        "selected_option": "slot_A",
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    action_bad, _ = validate_and_wrap_action(raw, policy_ctx)
    sim_result_bad = apply_action(state, action_bad)
    
    report2 = evaluate(base_scenario, sim_result_bad, candidate_slots)
    assert report2.status == EvaluationStatus.FAIL
    assert report2.assertions[0].actual == "Overlap"

def test_missing_candidate_slots_produces_error(base_scenario, policy_ctx):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (NoCalendarOverlap(),))
    
    # No candidate_slots passed
    report = evaluate(base_scenario, sim_result)
    assert report.status == EvaluationStatus.ERROR
    assert "ERR_EVALUATION_FAILURE" in report.assertions[0].error

def test_missing_action_evaluates_gracefully(base_scenario):
    state = SimulationState.from_scenario(base_scenario)
    # Simulate a crash or failure to act
    sim_result = SimulationResult(
        status="ERR_INVALID_ACTION",
        action_type=None,
        state_before=state,
        state_after=None,
        action_record=None,
        error="Agent failed"
    )
    
    mutate_scenario_assertions(base_scenario, (ActionTypeEquals(expected="PROPOSE_TIMES"),))
    report = evaluate(base_scenario, sim_result)
    assert report.status == EvaluationStatus.FAIL
    assert report.assertions[0].passed is False

def test_calendar_mutated_fails(base_scenario, policy_ctx, candidate_slots):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    # Artificially mutate the returned calendar
    from nexus.core.domain.calendar import CalendarEvent, Visibility
    bad_calendar = state.calendar + (CalendarEvent(id="fake", title="fake", start=datetime.now(timezone.utc), end=datetime.now(timezone.utc), visibility=Visibility.PUBLIC),)
    object.__setattr__(sim_result.state_after, "calendar", bad_calendar)
    
    mutate_scenario_assertions(base_scenario, (CalendarUnchanged(),))
    report = evaluate(base_scenario, sim_result, candidate_slots)
    assert report.status == EvaluationStatus.FAIL
    assert report.assertions[0].actual == "Changed"

def test_evaluation_determinism(base_scenario, policy_ctx, candidate_slots):
    action = get_propose_action(policy_ctx)
    state = SimulationState.from_scenario(base_scenario)
    sim_result = apply_action(state, action)
    
    mutate_scenario_assertions(base_scenario, (ActionTypeEquals(expected="PROPOSE_TIMES"),))
    
    report1 = evaluate(base_scenario, sim_result, candidate_slots)
    report2 = evaluate(base_scenario, sim_result, candidate_slots)
    
    # Deterministic equality
    assert report1 == report2
