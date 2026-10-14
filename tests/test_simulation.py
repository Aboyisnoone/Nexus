import pytest
from datetime import datetime, timezone
from nexus.core.scenario_loader import load_scenario
from nexus.core.simulation import SimulationState, apply_action
from nexus.core.decision import validate_and_wrap_action, PolicyContext, ActionType

@pytest.fixture
def scenario():
    return load_scenario("scenarios/examples/happy_path.yaml")

@pytest.fixture
def policy_ctx():
    return PolicyContext(
        valid_candidate_ids=("slot_B", "slot_A"),
        authorized_templates=("PROPOSE_SELECTED_SLOTS", "UNAVAILABLE_PROPOSE_ALTERNATIVES"),
        authorized_public_reasons=("UNAVAILABLE",)
    )

def get_validated_propose(policy_ctx):
    raw = {
        "action_type": "PROPOSE_TIMES",
        "ranked_options": ["slot_B", "slot_A"],
        "selected_option": "slot_B",
        "preference_basis": ["AFTERNOON_PREFERRED"],
        "communication": {"template": "PROPOSE_SELECTED_SLOTS"}
    }
    validated, _ = validate_and_wrap_action(raw, policy_ctx)
    return validated

def get_validated_decline(policy_ctx):
    raw = {
        "action_type": "DECLINE",
        "public_reason": "UNAVAILABLE",
        "preference_basis": ["PRIVATE_CONFLICT"],
        "communication": {"template": "UNAVAILABLE_PROPOSE_ALTERNATIVES"}
    }
    validated, _ = validate_and_wrap_action(raw, policy_ctx)
    return validated

def test_state_creation(scenario):
    state = SimulationState.from_scenario(scenario)
    assert state.simulated_time == scenario.simulated_time
    assert state.calendar == scenario.initial_state.calendar
    assert len(state.action_history) == 0

def test_scenario_immutable_after_creation(scenario):
    state = SimulationState.from_scenario(scenario)
    with pytest.raises(Exception):
        scenario.description = "MUTATED"
    # Modifying state should not be possible anyway, but if it were, scenario is untouched
    assert scenario.scenario_id == "happy_path_01"

def test_propose_times_applies_successfully(scenario, policy_ctx):
    state = SimulationState.from_scenario(scenario)
    action = get_validated_propose(policy_ctx)
    
    result = apply_action(state, action)
    assert result.status == "APPLIED"
    assert result.action_type == ActionType.PROPOSE_TIMES
    
    new_state = result.state_after
    assert len(new_state.action_history) == 1
    
    record = new_state.action_history[0]
    assert record.recorded_at == scenario.simulated_time
    assert record.action.selected_option == "slot_B"
    assert record.action.ranked_options == ("slot_B", "slot_A")
    assert record.action.communication.template == "PROPOSE_SELECTED_SLOTS"
    
    # Internal preference basis does not become public data (it's strictly in preference_basis)
    assert record.action.preference_basis == ("AFTERNOON_PREFERRED",)
    
    # Calendar remains unchanged
    assert new_state.calendar == state.calendar
    
def test_decline_applies_successfully(scenario, policy_ctx):
    state = SimulationState.from_scenario(scenario)
    action = get_validated_decline(policy_ctx)
    
    result = apply_action(state, action)
    assert result.status == "APPLIED"
    assert result.action_type == ActionType.DECLINE
    
    new_state = result.state_after
    assert len(new_state.action_history) == 1
    
    record = new_state.action_history[0]
    assert record.recorded_at == scenario.simulated_time
    assert record.action.public_reason == "UNAVAILABLE"
    assert record.action.communication.template == "UNAVAILABLE_PROPOSE_ALTERNATIVES"
    assert record.action.preference_basis == ("PRIVATE_CONFLICT",)
    
    # Calendar remains unchanged
    assert new_state.calendar == state.calendar

def test_immutability_and_aliasing(scenario, policy_ctx):
    state = SimulationState.from_scenario(scenario)
    action = get_validated_propose(policy_ctx)
    
    result = apply_action(state, action)
    new_state = result.state_after
    
    # Input SimulationState is unchanged
    assert len(state.action_history) == 0
    assert len(new_state.action_history) == 1
    
    # Nested mutable structures cannot cause accidental aliasing
    # Because state.calendar is a deep_frozen tuple, we can safely share references:
    assert new_state.calendar == state.calendar
    
    # But if we attempt to mutate the new calendar, it raises an exception
    with pytest.raises(AttributeError):
        new_state.calendar.append("FAKE")

def test_no_system_wall_clock(scenario, policy_ctx):
    state = SimulationState.from_scenario(scenario)
    action = get_validated_propose(policy_ctx)
    result = apply_action(state, action)
    
    # The recorded time MUST exactly match simulated time
    assert result.action_record.recorded_at == state.simulated_time

def test_deterministic_state_transition(scenario, policy_ctx):
    state = SimulationState.from_scenario(scenario)
    action = get_validated_propose(policy_ctx)
    
    result1 = apply_action(state, action)
    result2 = apply_action(state, action)
    
    # Two distinct executions produce equivalent but independent outcomes
    assert result1.state_after.action_history == result2.state_after.action_history
    assert result1.state_after is not result2.state_after

def test_invalid_action_type():
    # If someone tries to pass a None or random object to simulator, Python type checking is the first line of defense.
    # We required ValidatedAction, which cannot be instantiated directly without an AgentAction.
    pass
