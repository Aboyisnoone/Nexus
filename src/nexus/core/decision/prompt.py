from typing import Dict, Any, List, Tuple
from datetime import datetime

from nexus.core.domain.scenario import Scenario
from nexus.core.domain.memory import MemoryItem
from nexus.core.scheduling.models import CandidateSlot

PROMPT_VERSION = "decision_prompt_v1"

class PromptBuilder:
    @staticmethod
    def build_decision_prompt(
        scenario: Scenario,
        simulated_time: datetime,
        candidates: Tuple[CandidateSlot, ...],
        memories: List[MemoryItem]
    ) -> Dict[str, Any]:
        '''
        Deterministically builds the prompt payload.
        '''
        
        # Serialize candidates
        candidates_json = []
        for i, c in enumerate(candidates):
            c_dict = c.model_dump(mode="json")
            c_dict["slot_id"] = f"slot_{i}"
            candidates_json.append(c_dict)
            
        # Serialize memories
        memory_json = []
        # Sort memories for determinism
        sorted_mems = sorted(memories, key=lambda m: (m.context_id, m.key, m.version, m.id))
        for m in sorted_mems:
            mem_dict = {
                "key": m.key,
                "value": m.value,
                "state": m.state.value if hasattr(m.state, "value") else m.state,
                "contradictions": [c.model_dump(mode="json") for c in m.contradictions]
            }
            memory_json.append(mem_dict)
            
        # Serialize context events
        events_json = [e.model_dump(mode="json") for e in scenario.events]
        
        prompt = {
            "version": PROMPT_VERSION,
            "simulated_time": simulated_time.isoformat(),
            "context": {
                "scenario_description": scenario.description,
                "events": events_json
            },
            "memory": memory_json,
            "candidates": candidates_json,
            "instruction": (
                "You are an autonomous scheduling agent. "
                "Analyze the context, constraints, and memory, then select the best candidate slot "
                "or indicate that no slots are viable.\n"
                "Return a strict JSON object matching one of the following schemas:\n\n"
                "1. When viable slots exist (action_type PROPOSE_TIMES):\n"
                "{\n"
                "  \"action_type\": \"PROPOSE_TIMES\",\n"
                "  \"ranked_options\": [\"slot_0\"],\n"
                "  \"selected_option\": \"slot_0\",\n"
                "  \"communication\": {\"template\": \"PROPOSE_SELECTED_SLOTS\"},\n"
                "  \"preference_basis\": [\"AFTERNOON_PREFERRED\"]\n"
                "}\n"
                "(Note: ranked_options must contain the valid slot_id strings from candidates in preferred order. selected_option must be in ranked_options. Allowed preference_basis values: AFTERNOON_PREFERRED, CLIENT_PRIORITY, PRIVATE_CONFLICT, or empty [])\n\n"
                "2. When no slots are viable or request cannot be accepted (action_type DECLINE):\n"
                "{\n"
                "  \"action_type\": \"DECLINE\",\n"
                "  \"ranked_options\": [],\n"
                "  \"selected_option\": null,\n"
                "  \"public_reason\": \"UNAVAILABLE\",\n"
                "  \"communication\": {\"template\": \"UNAVAILABLE_PROPOSE_ALTERNATIVES\"},\n"
                "  \"preference_basis\": []\n"
                "}\n"
                "Return ONLY the raw JSON object without markdown or code fences."
            )
        }
        return prompt

    @staticmethod
    def extract_candidate_ids(candidates: Tuple[CandidateSlot, ...]) -> Tuple[str, ...]:
        return tuple(f"slot_{i}" for i in range(len(candidates)))
