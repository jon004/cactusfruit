import os
import requests
import time
import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from documentutils.models import Chunk, EmbeddedChunk

class ChunkEmbedder:
    def __init__(self):
        # Dynamically fetch configuration from environment variables
        # Set these in your AWS Lambda configuration
        self.base_url = os.getenv("EMBEDDER_API_URL", "http://localhost:8000")
        self.model_path = os.getenv("EMBEDDER_MODEL_PATH", "/models/model.gguf")
        
        self.embed_doc_url = f"{self.base_url}/embed-doc"
        self.embed_query_url = f"{self.base_url}/embed-query"
        self.token_count_url = f"{self.base_url}/token/count"
        
        self.max_retries = 10
        self.retry_delay = 1.5
        self.logger = logging.getLogger(__name__)

    def _safe_request(self, url: str, text: str) -> Dict[str, Any]:
        """Handles the POST request to the remote embedding Lambda."""
        for attempt in range(self.max_retries):
            try:
                payload = {
                    "model_path": self.model_path,
                    "content": text
                }
                response = requests.post(url, json=payload, timeout=120)
                if response.status_code == 200:
                    return response.json() 
                if response.status_code == 429:
                    time.sleep(self.retry_delay)
                    continue
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Connection failed after {self.max_retries} attempts: {e}")
                    raise Exception(f"Connection failed: {e}")
                time.sleep(self.retry_delay)
        return {}

    def embed_document_chunks(self, chunks: List[Chunk]) -> List[EmbeddedChunk]:
        embedded_list = []
        for chunk in chunks:
            data = self._safe_request(self.embed_doc_url, chunk.prefixed_text)
            # The remote API response structure is handled here
            vector = data.get("embedding", [])
            embedded_list.append(EmbeddedChunk(
                prefixed_text=chunk.prefixed_text,
                raw_text=chunk.raw_text,
                metadata=chunk.metadata,
                vector=vector
            ))
        return embedded_list

    def embed_query(self, query_text: str) -> List[float]:
        data = self._safe_request(self.embed_query_url, query_text)
        return data.get("embedding", [])

    def token_count(self, text: str) -> int:
        data = self._safe_request(self.token_count_url, text)
        return data.get("token_count", 0)
    
    # find_best_match and rank_chunks remain unchanged as they are local computation logic
