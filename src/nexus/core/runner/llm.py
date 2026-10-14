from typing import Protocol, Dict, Any, Tuple
import hashlib
import json

class ReplayRecordingNotFoundError(Exception):
    pass

class ReplayInputMismatchError(Exception):
    pass

def compute_prompt_hash(prompt: Dict[str, Any]) -> str:
    # Deterministic serialization for hashing
    serialized = json.dumps(prompt, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

class LLMClient(Protocol):
    def generate(self, prompt: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        '''
        Generate a response.
        Returns:
            Tuple containing:
            - response_json: The structured JSON response from the LLM
            - model_id: The ID of the model used
        '''
        ...
