# EC2Embedder.py
import requests
import os
from typing import List

class Embedder:
    def __init__(self):
        # Targets the default open-source llama-server running in production/EC2 environment
        self.base_url = os.getenv("EC2_LLAMA_URL", "http://127.0.0.1:8081")

    def embed_document(self, text: str) -> List[float]:
        response = requests.post(f"{self.base_url}/embed-doc", json={"content": text}, timeout=30)
        response.raise_for_status()
        return response.json().get("embedding", [])

    def embed_query(self, query_text: str) -> List[float]:
        response = requests.post(f"{self.base_url}/embed-query", json={"content": query_text}, timeout=30)
        response.raise_for_status()
        return response.json().get("embedding", [])

    def token_count(self, text: str) -> int:
        response = requests.post(f"{self.base_url}/token/count", json={"content": text}, timeout=30)
        response.raise_for_status()
        return response.json().get("token_count", 0)
