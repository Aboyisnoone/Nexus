import os
import json
import time
import httpx
from typing import Dict, Any, Tuple

from nexus.core.runner.llm import LLMClient

class GeminiLLMClient(LLMClient):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_id = os.environ.get("GEMINI_MODEL_ID", "gemini-3.1-flash-lite")
            
    def generate(self, prompt: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing. Cannot call real LLM API.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": json.dumps(prompt, indent=2)}]
            }],
            "generationConfig": {
                "temperature": 0.0,
                "responseMimeType": "application/json"
            }
        }
        
        max_retries = 3
        last_error = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(url, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    break
                elif response.status_code in (429, 503) and attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    raise RuntimeError(f"LLM API Error {response.status_code}: {response.text}")
            except httpx.RequestError as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"LLM Connection Error: {str(e)}") from e
        else:
            if last_error:
                raise RuntimeError(f"LLM Connection Error: {str(last_error)}")
            
        try:
            text_response = result["candidates"][0]["content"]["parts"][0]["text"]
            structured_response = json.loads(text_response)
        except (KeyError, IndexError, json.JSONDecodeError):
            return {"_raw_unparseable_output": text_response if 'text_response' in locals() else str(result)}, self.model_id
            
        return structured_response, self.model_id
