from typing import Tuple
from nexus.core.domain.scenario import Scenario
from nexus.core.decision.validator import PolicyContext

class ScenarioPolicyAdapter:
    '''
    Adapter to derive PolicyContext configurations from a Scenario.
    
    The frozen NEXUS v0.1 Scenario model genuinely lacks a dedicated 
    PolicyConstraints field. This adapter extracts them deterministically.
    '''
    
    @staticmethod
    def extract_policy_context(scenario: Scenario, valid_candidate_ids: Tuple[str, ...]) -> PolicyContext:
        if scenario.events:
            for event in scenario.events:
                if event.payload and "policy_constraints" in event.payload:
                    return PolicyContext(
                        valid_candidate_ids=valid_candidate_ids,
                        **event.payload["policy_constraints"]
                    )
                    
        return PolicyContext(
            valid_candidate_ids=valid_candidate_ids,
            authorized_templates=("PROPOSE_SELECTED_SLOTS", "UNAVAILABLE_PROPOSE_ALTERNATIVES"),
            authorized_public_reasons=("UNAVAILABLE",)
        )
