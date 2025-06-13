import os
import time

import pytest
import requests

COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.yml")
BASE_TIMEOUT = int(os.getenv("HARNESS_TIMEOUT", 30))

@pytest.fixture(scope="session", autouse=True)
def _stack_up():
    """Spin up the BizDev stack for the duration of the session."""
    import atexit
import subprocess
    proc = subprocess.Popen(
        ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.wait()
    atexit.register(
        lambda: subprocess.call(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"])
    )
    time.sleep(10)  # allow services to warm
    yield

def test_ping_chain():
    ci = requests.get("http://localhost:8080/ping", timeout=BASE_TIMEOUT).json()
    hm = requests.get("http://localhost:8000/ping", timeout=BASE_TIMEOUT).json()
    assert ci["msg"].startswith("contact-ingest"), "contact-ingest unreachable"
    assert hm["msg"].startswith("hubspot-mock"), "hubspot-mock unreachable"
