# cactusfruit/sdk/llmserverclient.py
import requests
import logging
from typing import List, Dict, Any, Optional

DEFAULT_LLM_SERVER_URL = "http://localhost:8287"
DEFAULT_EMBEDDER_MODEL_PATH = "models/all-MiniLM-L6-v2"

class LlmServerClient:
    def __init__(self, base_url: str = DEFAULT_LLM_SERVER_URL, embedder_model_path: str = DEFAULT_EMBEDDER_MODEL_PATH, generator_model_path: str = DEFAULT_EMBEDDER_MODEL_PATH):
        self.base_url = base_url
        self.embedder_model_path = embedder_model_path
        self.generator_model_path = generator_model_path
        self.logger = logging.getLogger(__name__)

    def _embedder_request(
        self, 
        url: str, 
        content: str, 
        model_path: Optional[str] = None
    ) -> Dict[str, Any]:
        active_model = model_path or self.embedder_model_path
        headers = {
            "X-Model-Path": active_model,
            "X-Content": content
        }
        payload = {
            "model_path": active_model,
            "content": content
        }
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()

    def embed_document(self, content: str, model_path: Optional[str] = None) -> List[float]:
        data = self._embedder_request(f"{self.base_url}/m/embed-doc", content, model_path)
        return data.get("embedding", [])

    def embed_query(self, content: str, model_path: Optional[str] = None) -> List[float]:
        data = self._embedder_request(f"{self.base_url}/m/embed-query", content, model_path)
        return data.get("embedding", [])

    def embed_token_count(self, content: str, model_path: Optional[str] = None) -> int:
        data = self._embedder_request(f"{self.base_url}/m/token/count", content, model_path)
        return data.get("token_count", 0)

    def generate(
        self, 
        role: str, 
        content: str, 
        params: dict = None, 
        model_path: Optional[str] = None,
        n_gpu_layers: int = 100,
        n_ctx: int = 2048,
        chat_template: Optional[str] = None
    ) -> str:
        active_model = model_path or self.generator_model_path
        headers = {
            "X-Model-Path": active_model,
            "X-Role": role,
            "X-Prompt": content,
            "X-N-Gpu-Layers": str(n_gpu_layers),
            "X-N-Ctx": str(n_ctx)
        }
        if chat_template:
            headers["X-Chat-Template"] = chat_template

        payload = {
            "model_path": active_model,
            "role": role,
            "content": content,
            "n_gpu_layers": n_gpu_layers,
            "n_ctx": n_ctx,
            **(params or {})
        }
        if chat_template:
            payload["chat_template"] = chat_template

        response = requests.post(f"{self.base_url}/m/prompt", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    def generate_with_image(
        self, 
        role: str, 
        content: str, 
        image_bytes: bytes, 
        mmproj_path: str, 
        model_path: Optional[str] = None,
        n_gpu_layers: int = 100,
        n_ctx: int = 2048,
        chat_template: Optional[str] = None
    ) -> str:
        active_model = model_path or self.generator_model_path
        headers = {
            "Content-Type": "application/octet-stream",
            "X-Model-Path": active_model,
            "X-Mmproj-Path": mmproj_path,
            "X-Role": role,
            "X-Prompt": content,
            "X-N-Gpu-Layers": str(n_gpu_layers),
            "X-N-Ctx": str(n_ctx)
        }
        
        if chat_template:
            headers["X-Chat-Template"] = chat_template

        response = requests.post(
            f"{self.base_url}/m/prompt/image",
            headers=headers,
            data=image_bytes,
            timeout=180
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
