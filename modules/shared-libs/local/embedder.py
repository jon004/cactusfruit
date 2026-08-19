# LocalEmbedder.py
import requests
import logging
from typing import List, Dict, Any
from configs import LLM_SERVER_URL, EMBEDDER_MODEL_PATH

class LocalEmbedder:
    def __init__(self, base_url: str = LLM_SERVER_URL, model_path: str = EMBEDDER_MODEL_PATH):
        self.base_url = base_url
        self.model_path = model_path
        self.embed_doc_url = f"{base_url}/m/embed-doc"
        self.embed_query_url = f"{base_url}/m/embed-query"
        self.token_count_url = f"{base_url}/m/token/count"
        self.logger = logging.getLogger(__name__)

    def _request(self, url: str, text: str) -> Dict[str, Any]:
        payload = {
            "model_path": self.model_path,
            "content": text
        }
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def embed_document(self, text: str) -> List[float]:
        data = self._request(self.embed_doc_url, text)
        return data.get("embedding", [])

    def embed_query(self, query_text: str) -> List[float]:
        data = self._request(self.embed_query_url, query_text)
        return data.get("embedding", [])

    def token_count(self, text: str) -> int:
        data = self._request(self.token_count_url, text)
        return data.get("token_count", 0)
