#!/usr/bin/env python3
"""CPU probe endpoint for the Alfred Agent Platform.

Expose GET /cpu returning current CPU usage and load-average in JSON.
"""

import os

import psutil
from fastapi import FastAPI

app = FastAPI(
    title="cpu-probe",
    description="CPU probe endpoint",
    version="1.0.0",
)

@app.get("/cpu")
async def cpu_probe():
    """Get current CPU usage percent and load average"""
    used_percent = psutil.cpu_percent()
    load_avg_1m, load_avg_5m, load_avg_15m = os.getloadavg()
    return {
        "used_percent": used_percent,
        "load_avg_1m": load_avg_1m,
        "load_avg_5m": load_avg_5m,
        "load_avg_15m": load_avg_15m,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9091)
