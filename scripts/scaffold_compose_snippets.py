#!/usr/bin/env python3
"""Scaffold compose.yml snippets for each service based on services.yaml"""

from pathlib import Path

import yaml

def load_services():
    """Load the canonical services list"""
    with open("services.yaml", "r") as f:
        services_data = yaml.safe_load(f)

    # Flatten the services list
    services = []
    for category, service_list in services_data.items():
        services.extend(service_list)
    return services

def create_compose_snippet(service_name, service_dir):
    """Create a default compose.yml snippet for a service"""
    compose_file = service_dir / "compose.yml"

    # Default snippet template
    snippet = {
        "services": {
            service_name: {
                "image": f"${{A
RED_REGISTRY}}/alfred-platform/{service_name}:${{A
RED_VERSION}}",
                "environment": [
                    "A
RED_ENVIRONMENT=${A
RED_ENVIRONMENT}",
                    "A
RED_LOG_LEVEL=${A
RED_LOG_LEVEL}",
                ],
                "restart": "unless-stopped",
                "networks": ["alfred-network"],
            }
        }
    }

    # Service-specific defaults
    if "db" in service_name or "postgres" in service_name:
        snippet["services"][service_name]["volumes"] = [
            f"{service_name}-data:/var/lib/postgresql/data"
        ]

    if service_name in ["redis", "vector-db"]:
        snippet["services"][service_name]["ports"] = []
        if service_name == "redis":
            snippet["services"][service_name]["ports"].append("${REDIS_PORT:-6379}:6379")
        elif service_name == "vector-db":
            snippet["services"][service_name]["ports"].append("${QDRANT_PORT:-6333}:6333")

    if service_name.endswith("-ui") or service_name in [
        "mission-control",
        "streamlit-chat",
    ]:
        snippet["services"][service_name]["ports"] = []
        base_port = 3000 if "mission" in service_name else 8501
        snippet["services"][service_name]["ports"].append(f"${{UI_PORT:-{base_port}}}:{base_port}")

    # Write the snippet
    compose_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(compose_file, "w") as f:
            yaml.dump(snippet, f, default_flow_style=False, sort_keys=False)
        print(f"Created: {compose_file}")
    except PermissionError:
        print(f"Skipped: {compose_file} (permission denied)")

def main():
    """Scaffold compose snippets for all services"""
    services = load_services()
    services_dir = Path("services")

    for service in services:
        service_dir = services_dir / service
        if not service_dir.exists():
            # Create directory for missing services
            try:
                service_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created directory: {service_dir}")
            except PermissionError:
                print(f"Warning: Cannot create directory for service: {service}")
                continue
        create_compose_snippet(service, service_dir)

if __name__ == "__main__":
    main()
