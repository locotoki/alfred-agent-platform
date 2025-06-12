#!/usr/bin/env python3
"""Service health check script to validate all services are running"""

import asyncio
import sys
from typing import Any, Dict, List

import aiohttp

SERVICES = {
    "alfred-bot": {"port": 8011, "health_endpoint": "/health/health"},
    "social-intel": {"port": 9000, "health_endpoint": "/health/health"},
    "legal-compliance": {"port": 9002, "health_endpoint": "/health/health"},
    "supabase-auth": {"port": 9999, "health_endpoint": "/health"},
    "supabase-rest": {"port": 3000, "health_endpoint": "/"},
    "supabase-realtime": {"port": 4000, "health_endpoint": "/"},
    "supabase-storage": {"port": 5000, "health_endpoint": "/health"},
    "grafana": {"port": 3002, "health_endpoint": "/api/health"},
    "prometheus": {"port": 9090, "health_endpoint": "/-/healthy"},
    "qdrant": {"port": 6333, "health_endpoint": "/health"},
}

async def check_service_health(service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Check health of a single service"""
    url = f"http://localhost:{config['port']}{config['health_endpoint']}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    return {
                        "service": service_name,
                        "status": "healthy",
                        "url": url,
                        "response_code": response.status,
                    }
                else:
                    return {
                        "service": service_name,
                        "status": "unhealthy",
                        "url": url,
                        "response_code": response.status,
                    }
    except Exception as e:
        return {"service": service_name, "status": "error", "url": url, "error": str(e)}

async def check_all_services() -> List[Dict[str, Any]]:
    """Check health of all services"""
    tasks = []
    for service_name, config in SERVICES.items():
        tasks.append(check_service_health(service_name, config))

    results = await asynciogather(*tasks)  # type: ignore[name-defined]
    return results

def print_health_report(results: List[Dict[str, Any]]):
    """Print formatted health report"""
    print("\n" + "=" * 50)
    print("SERVICE HEALTH CHECK REPORT")
    print("=" * 50 + "\n")

    healthy_count = 0
    unhealthy_count = 0
    error_count = 0

    for result in results:
        status = result["status"]
        service = result["service"]

        if status == "healthy":
            symbol = "✅"
            healthy_count += 1
        elif status == "unhealthy":
            symbol = "⚠️"
            unhealthy_count += 1
        else:
            symbol = "❌"
            error_count += 1

        print(f"{symbol} {service:<20} {status.upper()}")

        if status == "error":
            print(f"   Error: {result['error']}")
        elif status == "unhealthy":
            print(f"   Response Code: {result['response_code']}")

    print("\n" + "-" * 50)
    print(f"Total Services: {len(results)}")
    print(f"Healthy: {healthy_count}")
    print(f"Unhealthy: {unhealthy_count}")
    print(f"Error: {error_count}")
    print("-" * 50 + "\n")

    if unhealthy_count + error_count > 0:
        print("❌ Some services are not healthy!")
        return False
    else:
        print("✅ All services are healthy!")
        return True

async def main():
    """Main entry point"""
    results = await check_all_services()
    all_healthy = print_health_report(results)

    # Exit with error code if any services are unhealthy
    sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    asyncio.run(main())
