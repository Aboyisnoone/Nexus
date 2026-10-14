from .models import SimulationState, SimulationResult, ActionRecord
from nexus.core.decision.validator import ValidatedAction

def apply_action(state: SimulationState, validated_action: ValidatedAction) -> SimulationResult:
    """
    Applies a validated action to the current state, returning a deterministic transition outcome.
    Calendar and Memory remain unmutated for v0.1 PROPOSE_TIMES and DECLINE.
    """
    action = validated_action.action
    
    # 1. Create the action record using simulated time
    record = ActionRecord(
        action=action,
        recorded_at=state.simulated_time,
        status="APPLIED"
    )
    
    # 2. Append to action history (creates new tuple, does not mutate existing)
    new_history = state.action_history + (record,)
    
    # 3. Create strictly isolated new state
    new_state = SimulationState(
        simulated_time=state.simulated_time,
        calendar=state.calendar, # Deeply immutable tuple, safe to share reference
        memory=state.memory,     # Deeply immutable tuple, safe to share reference
        action_history=new_history
    )
    
    return SimulationResult(
        status="APPLIED",
        action_type=action.action_type,
        state_before=state,
        state_after=new_state,
        action_record=record
    )
