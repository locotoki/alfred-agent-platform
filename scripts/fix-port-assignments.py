#!/usr/bin/env python3
"""
Fix port conflicts in docker-compose.yml by assigning unique ports to each service.
"""

import sys
from pathlib import Path

import yaml

# Port remappings to fix conflicts
PORT_REMAPPINGS = {
    "slack_mcp_gateway": {"old": "3000:3000", "new": "3010:3000"},
    "slack-adapter": {"old": "3001:8000", "new": "3011:8000"},
    "hubspot-mock": {"old": "8000:8000", "new": "8088:8080"},
}

def fix_port_conflicts(compose_file):
    """Fix port conflicts in docker-compose.yml"""

    # Read the compose file
    with open(compose_file, "r") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    changes_made = []

    for service_name, remapping in PORT_REMAPPINGS.items():
        if service_name in services and "ports" in services[service_name]:
            ports = services[service_name]["ports"]
            for i, port in enumerate(ports):
                if isinstance(port, str) and port.startswith(remapping["old"].split(":")[0] + ":"):
                    old_port = port
                    new_port = remapping["new"]
                    # Preserve comments if any
                    if "#" in port:
                        comment = port.split("#")[1]
                        new_port = f"{remapping['new']}  #{comment}"
                    ports[i] = new_port
                    changes_made.append(f"{service_name}: {old_port} -> {new_port}")

    # Create backup
    backup_file = compose_file.with_suffix(".yml.backup")
    compose_file.rename(backup_file)
    print(f"✅ Created backup: {backup_file}")

    # Write updated compose file
    with open(compose_file, "w") as f:
        yaml.dump(compose_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print("\n📝 Port changes made:")
    for change in changes_made:
        print(f"  - {change}")

    return len(changes_made) > 0

def main():
    compose_file = Path("docker-compose.yml")

    if not compose_file.exists():
        print("❌ docker-compose.yml not found!")
        sys.exit(1)

    print("🔧 Fixing port conflicts in docker-compose.yml...")

    if fix_port_conflicts(compose_file):
        print("\n✅ Port conflicts fixed!")
        print("\n🎯 Next steps:")
        print("  1. Review the changes: diff docker-compose.yml docker-compose.yml.backup")
        print("  2. Update any override files to remove port configurations")
        print("  3. Restart services: docker-compose down && docker-compose up -d")
    else:
        print("\n✅ No port conflicts found!")

if __name__ == "__main__":
    main()
