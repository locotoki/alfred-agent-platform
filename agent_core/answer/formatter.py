"""Citation Assembler & Answer Formatter.

Takes (query, retrieved_passages) and returns a dict:

{
  "answer": "<LLM-generated answer>",
  "citations": [
      {"id": <chunk_id>, "snippet": "...", "score": 0.89}
  ]
}

Current stub echoes the top-k passages; GPT call will be
added after ADR-013 is accepted.
"""

from __future__ import annotations

from typing import Dict, List

def assemble_answer(query: str, passages: List[Dict]) -> Dict:  # type: ignore
    """Return assembled answer with citations.

    Very first placeholder that returns the first passage as 'answer'
    and passes through citations unchanged.
    """
    if not passages:
        return {"answer": "No information available.", "citations": []}

    best = passages[0]
    return {
        "answer": best.get("snippet", "…"),
        "citations": passages[:5],  # TODO: score filter & dedupe
    }
