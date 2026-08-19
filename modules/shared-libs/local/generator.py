# LocalGenerator.py
import requests
import logging
from typing import Dict, Any
from configs import LLM_SERVER_URL, CHAT_MODEL_PATH

class LocalGenerator:
    def __init__(self, base_url: str = LLM_SERVER_URL, model_path: str = CHAT_MODEL_PATH):
        self.base_url = base_url
        self.model_path = model_path
        self.prompt_url = f"{base_url}/m/prompt"
        self.logger = logging.getLogger(__name__)

    def generate(self, role: str, content: str, params: dict = None) -> str:
        payload = {
            "model_path": self.model_path,
            "role": role,
            "content": content,
            **(params or {})
        }
        response = requests.post(self.prompt_url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
