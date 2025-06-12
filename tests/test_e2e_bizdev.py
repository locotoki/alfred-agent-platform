import json
import os
import pathlib
import subprocess
import time

import requests

def test_e2e():
    # spin up services
    env = os.environ.copy()
    env["COMPOSE_PROFILES"] = "core:bizdev"
    proc = subprocess.Popen(["docker", "compose", "up", "-d"], env=env)
    proc.wait()
    try:
        # give containers 20s to boot
        time.sleep(20)
        # drop event file
        data_dir = pathlib.Path("services/contact-ingest/data")
        data_dir.mkdir(exist_ok=True)
        data_dir.joinpath("smoke.jsonl").write_text(
            json.dumps(
                {
                    "email": "e2e@example.com",
                    "source": "web",
                    "timestamp": "2025-05-28T12:00:00Z",
                    "payload": {"firstName": "E2E", "lastName": "Smoke"},
                }
            )
            + "\n"
        )
        # wait for ingestion
        time.sleep(10)
        r = requests.get("http://localhost:8081/healthz", timeout=5)
        assert r.ok and r.json()["processed"] >= 1
    finally:
        subprocess.run(["docker", "compose", "down", "-v"], env=env, check=False)
