# EC2Generator.py
import requests
import os

class Generator:
    def __init__(self):
        # Targets the default open-source llama-server or sagemaker endpoint layout used in EC2/production
        self.base_url = os.getenv("LLAMA_URL", "http://127.0.0.1:8081")

    def generate(self, role: str, content: str, params: dict = None) -> str:
        full_prompt = f"<|im_start|>{role}\n{content}<|im_end|>\n<|im_start|>assistant\n"
        payload = {"prompt": full_prompt, **(params or {})}
        response = requests.post(f"{self.base_url}/completion", json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("content", "").strip()
