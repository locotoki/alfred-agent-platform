"""HubSpot Mock Service API."""

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="HubSpot-Mock", version="0.1.0")
@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"msg": "hubspot-mock alive"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8095)
