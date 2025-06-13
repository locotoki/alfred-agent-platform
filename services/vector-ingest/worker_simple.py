"""Vector ingestion worker with ML functionality (no langchain dependency)."""

import json
import logging
import os
import time
import uuid
from typing import List, Optional

import requests
import uvicorn
from cloudevents.http import CloudEvent
from fastapi import FastAPI, HTTPException, Response
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Vector Ingest Service")

# Initialize ML components (lazy loading)
MODEL: Optional[SentenceTransformer] = None

def get_model():
    """Lazy load the sentence transformer model."""
    global MODEL
    if MODEL is None:
        model_name = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        logger.info(f"Loading model: {model_name}")
        MODEL = SentenceTransformer(model_name)
    return MODEL

def simple_text_splitter(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> List[str]:
    """Simple text splitter without langchain dependency."""
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # Calculate end position
        end = start + chunk_size

        # If we're not at the end, try to find a good break point
        if end < text_length:
            # Look for sentence boundaries
            for sep in [". ", "! ", "? ", "\n\n", "\n", " "]:
                last_sep = text.rfind(sep, start + chunk_overlap, end)
                if last_sep != -1:
                    end = last_sep + len(sep)
                    break

        # Add the chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position
        start = end - chunk_overlap if end < text_length else text_length

    return chunks

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "vector-ingest",
        "mode": "simple",
        "model_loaded": MODEL is not None,
    }

@app.get("/healthz")
def healthz():
    """Simple health probe."""
    return {"status": "ok"}

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Vector Ingest Service",
        "version": "1.0.0",
        "health": "/health",
        "mode": "simple ML support (no langchain)",
    }

@app.post("/ingest")
async def ingest(event: dict):
    """Handle vector ingestion requests."""
    try:
        # For now, simplified auth handling
        # TODO: Implement proper auth verification

        data = event.get("data", {})
        if isinstance(data, str):
            data = json.loads(data)

        tenant = data.get("tenant", "default")
        doc_id = data.get("id", str(uuid.uuid4()))
        text = data.get("text", "")

        if not text:
            raise HTTPException(status_code=400, detail="No text provided for ingestion")

        # Process text
        chunks = simple_text_splitter(text)
        model = get_model()
        vectors = model.encode(chunks).tolist()

        payload = {
            "tenant": tenant,
            "doc_id": doc_id,
            "ttl_days": data.get("ttl_days", 90),
            "chunks": chunks,
            "vectors": vectors,
        }

        # Send to vector database
        vector_db_url = os.getenv("VECTOR_DB_URL", "http://vector-db:6333")
        response = requests.post(f"{vector_db_url}/ingest", json=payload, timeout=5)
        response.raise_for_status()

        logger.info(f"[{tenant}] ingested {len(chunks)} chunks for {doc_id}")

        return {
            "status": "success",
            "doc_id": doc_id,
            "chunks": len(chunks),
            "vectors": len(vectors),
        }

    except Exception as e:
        logger.error(f"Error processing ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
