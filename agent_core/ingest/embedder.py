"""Embedder module.

Light wrapper around OpenAI embeddings (ada-002).
Provides `embed(texts)` that returns a list of vectors.
"""

import os
from typing import List

import backoff
import openai

openai.api_key = os.getenv("OPENAI_API_KEY", "sk-placeholder")
EMBED_MODEL = "text-embedding-ada-002"

@backoff.on_exception(backoff.expo, openai.error.RateLimitError, max_time=60)  # type: ignore  # type: ignore
def _embed_one(text: str) -> List[float]:
    rsp = openai.Embedding.create(input=text, model=EMBED_MODEL)  # type: ignore
    return rsp["data"][0]["embedding"]  # type: ignore

def embed(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts using OpenAI ada-002."""
    return [_embed_one(t) for t in texts]
