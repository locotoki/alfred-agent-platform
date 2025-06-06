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
        provider: Provider name ("openai" or "claude")
        **kwargs: Provider-specific parameters

    Returns:
        LLMAdapter instance
    """
    if provider == "openai":
        return OpenAIAdapter(**kwargs)
    elif provider == "claude":
        return ClaudeAdapter(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
