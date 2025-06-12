"""LLM Adapter implementation for Alfred Core.

This module implements the Strategy/Adapter pattern for LLM providers, starting with
OpenAI GPT-4o-Turbo as the primary provider and Claude 3 Sonnet as a fallback option.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import structlog
from prometheus_client import Counter

# Prometheus metrics
llm_tokens_total = Counter(
    "alfred_llm_tokens_total",
    "Total tokens used across all LLM calls",
    ["model", "operation"],
)

llm_requests_total = Counter("alfred_llm_requests_total", "Total LLM requests", ["model", "status"])

logger = structlog.get_logger(__name__)


class Message:
    """Represent a message in the conversation."""

    def __init__(self, role: str, content: str):
        """Initialize a new message.

        Args:
            role: The role of the message sender (e.g., 'user', 'system', 'assistant')
            content: The content of the message
        """
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        """Convert the message to a dictionary format.

        Returns:
            A dictionary with role and content keys
        """
        return {"role": self.role, "content": self.content}


class LLMAdapter(ABC):
    """Define interface for language model adapters."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate a response from the LLM.

        Args:
            messages: List of messages in the conversation
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated response as string or async iterator of chunks
        """
        ...

    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for the given text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        ...


class OpenAIAdapter(LLMAdapter):
    """Implement adapter for OpenAI GPT-4o-Turbo model."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-turbo"):
        """Initialize the OpenAI adapter.

        Args:
            api_key: OpenAI API key (falls back to OPENAI_API_KEY env var)
            model: Model name to use (default: gpt-4o-turbo)

        Raises:
            ValueError: If no API key is provided
        """
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        # Lazy import to avoid dependency issues
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Return lazy-loaded OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client

    async def generate(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate text using OpenAI API."""
        try:
            message_dicts = [msg.to_dict() for msg in messages]

            params = {
                "model": self.model,
                "messages": message_dicts,
                "temperature": temperature,
                "stream": stream,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Add any additional kwargs
            params.update(kwargs)

            response = await self.client.chat.completions.create(**params)

            llm_requests_total.labels(model=self.model, status="success").inc()

            if stream:
                return self._stream_response(response)
            else:
                content = response.choices[0].message.content

                # Track token usage
                if hasattr(response, "usage"):
                    llm_tokens_total.labels(model=self.model, operation="completion").inc(
                        response.usage.total_tokens
                    )

                return str(content)

        except Exception as e:
            llm_requests_total.labels(model=self.model, status="error").inc()
            logger.error("OpenAI API error", error=str(e), model=self.model)
            raise

    async def _stream_response(self, response: Any) -> AsyncIterator[str]:
        """Stream response chunks from OpenAI API."""
        total_tokens = 0
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                total_tokens += self.estimate_tokens(content)
                yield content

        # Track token usage for streamed responses
        llm_tokens_total.labels(model=self.model, operation="stream_completion").inc(total_tokens)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using simple heuristic.

        Note: This is a rough estimate. For accurate counting,
        use tiktoken library.
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4


class OllamaAdapter(LLMAdapter):
    """Implement adapter for local Ollama models."""

    def __init__(self, model: str = "llama3:8b", base_url: str = "http://localhost:11434"):
        """Initialize the Ollama adapter.

        Args:
            model: Model name to use (default: llama3:8b)
            base_url: Ollama API base URL (default: http://localhost:11434)
        """
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Return HTTP client for Ollama API."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)
        return self._client

    async def generate(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate text using Ollama API."""
        try:
            # Convert messages to Ollama format
            prompt = self._format_messages(messages)

            params = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                },
            }

            if max_tokens:
                params["options"]["num_predict"] = max_tokens

            # Add any additional kwargs to options
            if kwargs:
                params["options"].update(kwargs)

            if stream:
                return self._stream_response(params)
            else:
                response = await self.client.post("/api/generate", json=params)
                response.raise_for_status()
                data = response.json()

                llm_requests_total.labels(model=self.model, status="success").inc()

                # Track token usage
                if "eval_count" in data:
                    llm_tokens_total.labels(model=self.model, operation="completion").inc(
                        data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    )

                return data["response"]

        except Exception as e:
            llm_requests_total.labels(model=self.model, status="error").inc()
            logger.error("Ollama API error", error=str(e), model=self.model)
            raise

    async def _stream_response(self, params: Dict[str, Any]) -> AsyncIterator[str]:
        """Stream response chunks from Ollama API."""
        total_tokens = 0

        async with self.client.stream("POST", "/api/generate", json=params) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json

                    try:
                        data = json.loads(line)
                        if "response" in data and data["response"]:
                            content = data["response"]
                            total_tokens += self.estimate_tokens(content)
                            yield content

                        if data.get("done"):
                            # Track final token usage
                            if "eval_count" in data:
                                actual_tokens = data.get("prompt_eval_count", 0) + data.get(
                                    "eval_count", 0
                                )
                                llm_tokens_total.labels(
                                    model=self.model, operation="stream_completion"
                                ).inc(actual_tokens)
                            break
                    except json.JSONDecodeError:
                        continue

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

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for Ollama models."""
        # Rough estimate for Llama models
        return len(text) // 4


class ClaudeAdapter(LLMAdapter):
    """Implement adapter for Anthropic Claude 3 Sonnet model."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        """Initialize the Claude adapter.

        Args:
            api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            model: Model name to use (default: claude-3-sonnet-20240229)

        Raises:
            ValueError: If no API key is provided
        """
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

        self._client: Optional[Any] = None

    @property
    def client(self) -> Any:
        """Return lazy-loaded Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    async def generate(
        self,
        messages: List[Message],
        *,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[str, AsyncIterator[str]]:
        """Generate text using Claude API."""
        try:
            # Claude expects system messages separately
            system_message = None
            user_messages = []

            for msg in messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    user_messages.append(msg.to_dict())

            params = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,  # Claude requires this
            }

            if system_message:
                params["system"] = system_message

            params.update(kwargs)

            response = await self.client.messages.create(**params)

            llm_requests_total.labels(model=self.model, status="success").inc()

            if stream:
                # Claude streaming requires different handling
                stream_response = await self.client.messages.create(**params, stream=True)
                return self._stream_response(stream_response)
            else:
                content = response.content[0].text

                # Track token usage
                if hasattr(response, "usage"):
                    llm_tokens_total.labels(model=self.model, operation="completion").inc(
                        response.usage.total_tokens
                    )

                return str(content)

        except Exception as e:
            llm_requests_total.labels(model=self.model, status="error").inc()
            logger.error("Claude API error", error=str(e), model=self.model)
            raise

    async def _stream_response(self, response: Any) -> AsyncIterator[str]:
        """Stream response chunks from Claude API."""
        total_tokens = 0
        async for chunk in response:
            if chunk.type == "content_block_delta":
                content = chunk.delta.text
                total_tokens += self.estimate_tokens(content)
                yield content

        llm_tokens_total.labels(model=self.model, operation="stream_completion").inc(total_tokens)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for Claude API."""
        # Similar rough estimate
        return len(text) // 4


# Factory function
def create_llm_adapter(provider: str = "openai", **kwargs: Any) -> LLMAdapter:
    """Create an LLM adapter instance.

    Args:
        provider: Provider name ("openai", "claude", or "ollama")
        **kwargs: Provider-specific parameters

    Returns:
        LLMAdapter instance
    """
    if provider == "openai":
        return OpenAIAdapter(**kwargs)
    elif provider == "claude":
        return ClaudeAdapter(**kwargs)
    elif provider == "ollama":
        return OllamaAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
