"""Health check command for Alfred platform."""

import json
import sys
from typing import Dict, List

import click
import requests
from rich.console import Console
from rich.table import Table

console = Console()
CORE_SERVICES = {
    "alfred-core": {
        "url": "http://localhost:8011/health",
        "critical": True,
    },
    "ui-chat": {
        "url": "http://localhost:3001/health",
        "critical": True,
    },
    "agent-orchestrator": {
        "url": "http://localhost:8012/health",
        "critical": True,
    },
    "model-registry": {
        "url": "http://localhost:8007/health",
        "critical": True,
    },
    "crm-sync": {
        "url": "http://localhost:8003/health",
        "critical": False,
    },
    "db-postgres": {
        "url": "http://localhost:5432/",
        "check_type": "tcp",
        "critical": True,
    },
    "redis": {
        "url": "http://localhost:6379/",
        "check_type": "tcp",
        "critical": True,
    },
}

OBSERVABILITY_SERVICES = {
    "prometheus": {
        "url": "http://localhost:9090/-/healthy",
        "critical": False,
    },
    "grafana": {
        "url": "http://localhost:3030/api/health",
        "critical": False,
    },
    "alertmanager": {
        "url": "http://localhost:9093/-/healthy",
        "critical": False,
    },
}


def check_service_health(name: str, config: Dict) -> Dict:
    """Check health of a single service."""
    result = {
        "name": name,
        "status": "unknown",
        "critical": config.get("critical", False),
        "error": None,
    }

    try:
        if config.get("check_type") == "tcp":
            # For TCP-only services, just check connectivity

            import socket

            host = config["url"].replace("http://", "").replace("/", "").split(":")[0]
            port = int(config["url"].replace("http://", "").replace("/", "").split(":")[1])
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.close()
            result["status"] = "healthy"
        else:
            # HTTP health check
            response = requests.get(config["url"], timeout=5)
            if response.status_code == 200:
                result["status"] = "healthy"
            else:
                result["status"] = "unhealthy"
                result["error"] = f"HTTP {response.status_code}"
    except Exception as e:
        result["status"] = "unreachable"
        result["error"] = str(e)

    return result


def print_health_table(results: List[Dict], title: str):
    """Print health check results in a table."""
    table = Table(title=title)
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Critical", style="yellow")
    table.add_column("Error", style="red")

    for result in results:
        status_style = "green" if result["status"] == "healthy" else "red"
        table.add_row(
            result["name"],
            f"[{status_style}]{result['status']}[/{status_style}]",
            "Yes" if result["critical"] else "No",
            result["error"] or "-",
        )

    console.print(table)


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--critical-only", is_flag=True, help="Check only critical services")
def health(output_json: bool, critical_only: bool):
    """Check health of Alfred platform services."""
    console.print("[bold blue]Alfred Platform Health Check[/bold blue]\n")

    # Check core services
    core_results = []
    for name, config in CORE_SERVICES.items():
        if critical_only and not config.get("critical", False):
            continue
        result = check_service_health(name, config)
        core_results.append(result)

    # Check observability services if not critical-only
    obs_results = []
    if not critical_only:
        for name, config in OBSERVABILITY_SERVICES.items():
            result = check_service_health(name, config)
            obs_results.append(result)

    # Output results
    if output_json:
        output = {
            "core_services": core_results,
            "observability_services": obs_results,
            "overall_status": (
                "healthy"
                if all(r["status"] == "healthy" for r in core_results if r["critical"])
                else "unhealthy"
            ),
        }
        print(json.dumps(output, indent=2))
    else:
        print_health_table(core_results, "Core Services")
        if obs_results:
            console.print()
            print_health_table(obs_results, "Observability Services")

        # Overall status
        critical_healthy = all(r["status"] == "healthy" for r in core_results if r["critical"])

        console.print()
        if critical_healthy:
            console.print("[bold green]✓ All critical services are healthy[/bold green]")
            sys.exit(0)
        else:
            console.print("[bold red]✗ Some critical services are unhealthy[/bold red]")
            sys.exit(1)


if __name__ == "__main__":
    health()
