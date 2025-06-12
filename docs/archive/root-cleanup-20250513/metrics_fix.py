#!/usr/bin/env python3
"""Script to fix Prometheus metrics content type."""

import re

# Path to health.py
HEALTH_FILE = "/app/libs/agent_core/health.py"
# Read the current file
with open(HEALTH_FILE, "r") as file:
    content = file.read()

# Fix the metrics endpoint
fixed_content = re.sub(
    r'@health_app\.get\("/metrics"\).*?def metrics\(\):.*?""".*?""".*?return prometheus_client\.generate_latest\(\)',
    '@health_app.get("/metrics")\n    async def metrics():\n        """Prometheus metrics endpoint."""\n        from fastapi.responses import Response\n        return Response(content=prometheus_client.generate_latest(), media_type="text/plain")',
    content,
    flags=re.DOTALL,
)

# Write the fixed content back
with open(HEALTH_FILE, "w") as file:
    file.write(fixed_content)

print(f"Fixed metrics endpoint in {HEALTH_FILE}")
