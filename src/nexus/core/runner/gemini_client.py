import os
import json
import time
import httpx
from typing import Dict, Any, Tuple

from nexus.core.runner.llm import LLMClient

FALLBACK_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it"
]

class GeminiLLMClient(LLMClient):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        configured_model = os.environ.get("GEMINI_MODEL_ID")
        self.models = [configured_model] if configured_model else []
        for m in FALLBACK_MODELS:
            if m not in self.models:
                self.models.append(m)
            
    def generate(self, prompt: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing. Cannot call real LLM API.")
            
        payload = {
            "contents": [{
                "parts": [{"text": json.dumps(prompt, indent=2)}]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json"
            }
        }
        
        last_error = None
        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            for attempt in range(2):
                try:
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(url, json=payload)
                    if response.status_code == 200:
                        result = response.json()
                        text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                        try:
                            structured = json.loads(text_response)
                        except (KeyError, IndexError, json.JSONDecodeError):
                            return {"_raw_unparseable_output": text_response}, model
                        return structured, model
                    elif response.status_code in (429, 503):
                        last_error = RuntimeError(f"Model {model} returned {response.status_code}: {response.text}")
                        time.sleep(1)
                        continue
                    else:
                        last_error = RuntimeError(f"Model {model} returned {response.status_code}: {response.text}")
                        break
                except httpx.RequestError as e:
                    last_error = RuntimeError(f"Model {model} connection error: {str(e)}")
                    time.sleep(1)
                    continue
                    
        raise last_error or RuntimeError("All candidate LLM models failed.")
