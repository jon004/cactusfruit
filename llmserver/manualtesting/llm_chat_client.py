"""
LLM Chat Client Module

Updated to match the /m/... API documentation specifications.
"""

import json
requests = __import__('requests')
from typing import Dict, List, Optional

class LLMChatClient:

    def __init__(self, base_url: str = "http://localhost:8080", default_model_path: str = "models/model.gguf"):
        """Initialize the chat client with the server's base URL and default model path.
        
        Args:
            base_url: The base URL of the LLM server (default: "http://localhost:8080")
            default_model_path: The default file path to the Llama model
        """
        self.base_url = base_url.rstrip('/')
        self.current_role = "user"  # Default role is 'user'
        self.default_model_path = default_model_path

    def set_role(self, role: str) -> None:
        """Set the role for the user's messages."""
        self.current_role = role.lower()

    def post_llm_prompt(self, message: str, model_path: Optional[str] = None) -> str:
        """Send a message to the LLM server prompt endpoint and return the response.

        Args:
            message: The message content to send
            model_path: Optional override for the Llama model path

        Returns:
            The assistant's response as a string
        """
        url = f"{self.base_url}/m/prompt"

        # Required fields based on POST /m/prompt docs: model_path, role, content
        payload = {
            "model_path": model_path or self.default_model_path,
            "role": self.current_role,
            "content": message
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            # Response (JSON) contains 'response' key
            if 'application/json' in response.headers.get('Content-Type', ''):
                data = response.json()
                return data.get("response", str(data))
            return response.text

        except requests.exceptions.RequestException as e:
            return f"Error communicating with server: {str(e)}"

    def post_llm_reset(self, model_path: Optional[str] = None) -> bool:
        """Reset the conversation context on the server.

        Args:
            model_path: Optional override for the Llama model path

        Returns:
            bool: True if reset was successful, False otherwise
        """
        url = f"{self.base_url}/m/reset/context"
        payload = {
            "model_path": model_path or self.default_model_path
        }
        try:
            # Expects plain text response: "VRAM Cleared for model"
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            return "VRAM Cleared" in response.text
        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR] Failed to reset context: {str(e)}")
            return False

    def get_llm_status(self) -> Dict:
        """Get the status of the LLM server (GET /m/status)."""
        url = f"{self.base_url}/m/status"
        try:
            response = requests.get(url)
            response.raise_for_status()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            return {"status": "error", "message": response.text.strip()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def get_llm_context(self, model_path: Optional[str] = None) -> Dict:
        """Get the current chat context from the server (POST /m/read/context).
        
        Args:
            model_path: Optional override for the Llama model path
            
        Returns:
            Dict containing the chat history list
        """
        url = f"{self.base_url}/m/read/context"
        payload = {
            "model_path": model_path or self.default_model_path
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            if 'application/json' in response.headers.get('Content-Type', ''):
                return response.json()
            return {"status": "error", "message": "Unexpected response format"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}

    def post_llm_prefill(self, messages: List[Dict[str, str]], model_path: Optional[str] = None) -> Dict:
        """Prefill the chat history (POST /m/prefill).
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            model_path: Optional override for the Llama model path
            
        Returns:
            Dict with status and message
        """
        url = f"{self.base_url}/m/prefill"
        payload = {
            "model_path": model_path or self.default_model_path,
            "messages": messages
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return {"status": "success", "message": response.text.strip()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": str(e)}
