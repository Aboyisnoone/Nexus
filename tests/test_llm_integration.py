import os
import pytest
from nexus.core.runner.gemini_client import GeminiLLMClient

@pytest.mark.skipif(
    not os.environ.get("NEXUS_REAL_LLM_TEST"),
    reason="Opt-in real LLM test requires NEXUS_REAL_LLM_TEST=1"
)
def test_real_gemini_client():
    client = GeminiLLMClient()
    prompt = {
        "instruction": "You are a test. Return exactly this JSON: {\"action_type\": \"PROPOSE_TIMES\"}"
    }
    response, model_id = client.generate(prompt)
    assert response.get("action_type") == "PROPOSE_TIMES"
    assert model_id == os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")
