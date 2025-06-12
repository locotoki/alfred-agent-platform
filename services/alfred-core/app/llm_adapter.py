"""Simple LLM Adapter for Ollama integration."""

import httpx
import json
from typing import Dict, Any, List


class Message:
    """Represent a message in the conversation."""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class OllamaAdapter:
    """Simple Ollama adapter for local LLM integration."""

    def __init__(self, model: str = "llama3:8b", base_url: str = "http://llm-service:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, messages: List[Message], **kwargs) -> str:
        """Generate response using Ollama API."""

        # Format messages for Ollama
        prompt = self._format_messages(messages)

        params = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        if "max_tokens" in kwargs:
            params["options"]["num_predict"] = kwargs["max_tokens"]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=params)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "Sorry, I couldn't generate a response.")
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return f"Error: {str(e)}"

    def _format_messages(self, messages: List[Message]) -> str:
        """Format messages for Ollama prompt."""
        formatted_parts = []

        for msg in messages:
            if msg.role == "system":
                formatted_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                formatted_parts.append(f"Human: {msg.content}")
            elif msg.role == "assistant":
                formatted_parts.append(f"Assistant: {msg.content}")

        # Add final prompt for assistant
        formatted_parts.append("Assistant:")

        return "\n\n".join(formatted_parts)
