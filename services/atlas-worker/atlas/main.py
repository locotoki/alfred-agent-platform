import os

from fastapi import FastAPI, Response

app = FastAPI()
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.0.0",
        "services": {"database": "ok", "rag": "ok", "pubsub": "ok"},
    }

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/metrics")
async def metrics():
    metrics_text = """# HELP service_up Service availability
# TYPE service_up gauge
service_up 1
# HELP service_requests_total Total requests processed
# TYPE service_requests_total counter
service_requests_total 0"""
    return Response(content=metrics_text, media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("atlas.main:app", host="0.0.0.0", port=port, reload=False)
