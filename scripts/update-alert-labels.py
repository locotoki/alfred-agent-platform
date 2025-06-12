#!/usr/bin/env python3
"""Update Prometheus alert rules with additional labels"""
# type: ignore
import re
import sys
from pathlib import Path

import yaml

def update_alert_labels(file_path: Path) -> None:
    """Update alert labels in a single file"""
    with open(file_path, "r") as f:
        content = f.read()

    # Parse YAML
    data = yaml.safe_load(content)

    if not data or "groups" not in data:
        print(f"Skipping {file_path}: No groups found")
        return

    modified = False

    for group in data["groups"]:
        if "rules" not in group:
            continue

        for rule in group["rules"]:
            if "alert" not in rule:
                continue

            # Extract service name from file name or alert name
            service_name = file_path.stem.replace("-", "_")
            if service_name == "mssql":
                service_name = "db_mssql"

            # Add labels if not present
            if "labels" not in rule:
                rule["labels"] = {}

            # Ensure severity is present
            if "severity" not in rule["labels"]:
                # Infer severity from alert name
                alert_name = rule["alert"].lower()
                if "critical" in alert_name:
                    rule["labels"]["severity"] = "critical"
                elif "warning" in alert_name:
                    rule["labels"]["severity"] = "warning"
                else:
                    rule["labels"]["severity"] = "info"
                modified = True

            # Add service label
            if "service" not in rule["labels"]:
                rule["labels"]["service"] = service_name
                modified = True

            # Add runbook label
            if "runbook" not in rule["labels"]:
                alert_name_snake = re.sub(r"([A-Z])", r"_\1", rule["alert"]).lower().strip("_")
                runbook_url = f"https://github.com/alfred-agent-platform-v2/runbooks/{alert_name_snake}.md"  # noqa: E501
                rule["labels"]["runbook"] = runbook_url
                modified = True

    if modified:
        # Write back with proper formatting
        with open(file_path, "w") as f:
            # Add header comment
            f.write(f"# {file_path}\n")
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, width=100)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")

def main():
    """Update all alert files"""
    alerts_dir = Path("charts/alerts")

    if not alerts_dir.exists():
        print(f"Error: {alerts_dir} does not exist")
        sys.exit(1)

    alert_files = list(alerts_dir.glob("*.yaml"))

    if not alert_files:
        print(f"No alert files found in {alerts_dir}")
        sys.exit(1)

    print(f"Found {len(alert_files)} alert files")

    for alert_file in alert_files:
        try:
            update_alert_labels(alert_file)
        except Exception as e:
            print(f"Error processing {alert_file}: {e}")
            continue

    print("Alert label update complete")

if __name__ == "__main__":
    main()
