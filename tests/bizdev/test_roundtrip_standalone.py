#!/usr/bin/env python3
"""Standalone BizDev roundtrip test - runs without pytest to avoid conftest issues."""

import atexit
import os
import subprocess
import sys
import time

import requests

COMPOSE_FILE = os.getenv("COMPOSE_FILE", "docker-compose.yml")
BASE_TIMEOUT = int(os.getenv("HARNESS_TIMEOUT", 30))

# Global process handle for cleanup
compose_proc = None

def cleanup():
    """Ensure docker compose is cleaned up."""
    global compose_proc
    if compose_proc:
        subprocess.call(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"])

# Register cleanup
atexit.register(cleanup)

def main():
    """Run the BizDev roundtrip test."""
    print("Starting BizDev stack...")

    # Start the stack
    global compose_proc
    compose_proc = subprocess.Popen(
        ["docker", "compose", "-f", COMPOSE_FILE, "up", "-d"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = compose_proc.communicate()

    if compose_proc.returncode != 0:
        print(f"Failed to start stack: {stderr.decode()}")
        return 1

    print("Waiting for services to warm up...")
    time.sleep(10)

    # Test the services
    try:
        print("Testing contact-ingest service...")
        ci_response = requests.get("http://localhost:8080/ping", timeout=BASE_TIMEOUT)
        ci_data = ci_response.json()
        assert ci_data["msg"].startswith("contact-ingest"), f"Unexpected response: {ci_data}"
        print("✓ contact-ingest is reachable")

        print("Testing hubspot-mock service...")
        hm_response = requests.get("http://localhost:8000/ping", timeout=BASE_TIMEOUT)
        hm_data = hm_response.json()
        assert hm_data["msg"].startswith("hubspot-mock"), f"Unexpected response: {hm_data}"
        print("✓ hubspot-mock is reachable")

        print("\nAll tests passed!")
        return 0

    except Exception as e:
        print(f"\nTest failed: {e}")
        return 1
    finally:
        cleanup()

if __name__ == "__main__":
    sys.exit(main())
