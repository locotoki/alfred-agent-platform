"""Chunker module.

Splits raw text or Markdown documents into overlapping
chunks suitable for embedding.  Initial algorithm:

* Recursive split on headings > paragraphs > sentences
* Target chunk size 1024 tokens; overlap 128 tokens
* Uses tiktoken for GPT-4o token counting
"""

from typing import List

try:
    import tiktoken
except ImportError:  # soft-dep for local dev
    tiktoken = None  # type: ignore

MAX_TOKENS = 1024
OVERLAP = 128

def _token_count(text: str) -> int:
    if not tiktoken:
        return len(text.split())  # fallback
    enc = tiktoken.encoding_for_model("gpt-4o")
    return len(enc.encode(text))

def chunk(text: str) -> List[str]:
    """Return a list of overlapping chunks.

    TODO: replace with recursive text-split algorithm.
    """
    tokens = text.split()
    step = MAX_TOKENS - OVERLAP
    chunks = [" ".join(tokens[i : i + MAX_TOKENS]) for i in range(0, len(tokens), step)]
    return chunks
