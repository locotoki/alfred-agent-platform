#!/usr/bin/env python3
"""Test script for validating Grafana dashboard JSON files.

Ensures dashboards are valid JSON and meet our standards.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

class DashboardValidator:
    """Validates Grafana dashboard JSON files."""

    def __init__(self, dashboard_dir: str):
        """Initialize the dashboard validator with a directory path."""
        self.dashboard_dir = Path(dashboard_dir)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_json_syntax(self, filepath: Path) -> bool:
        """Validate JSON syntax."""
        try:
            with open(filepath, "r") as f:
                json.load(f)
            return True
        except json.JSONDecodeError as e:
            self.errors.append(f"{filepath}: Invalid JSON - {e}")
            return False

    def validate_dashboard_structure(self, filepath: Path, data: Dict[str, Any]) -> bool:
        """Validate dashboard has required fields."""
        required_fields = ["dashboard"]
        dashboard_fields = ["uid", "title", "panels", "templating", "time", "refresh"]

        # Check top-level structure
        for field in required_fields:
            if field not in data:
                self.errors.append(f"{filepath}: Missing required field '{field}'")
                return False

        # Check dashboard fields
        dashboard = data["dashboard"]
        for field in dashboard_fields:
            if field not in dashboard:
                self.errors.append(f"{filepath}: Missing dashboard field '{field}'")
                return False

        return True

    def validate_panels(self, filepath: Path, panels: List[Dict[str, Any]]) -> bool:
        """Validate panel configurations."""
        valid = True

        for i, panel in enumerate(panels):
            panel_id = panel.get("id", f"index_{i}")

            # Required panel fields
            required = ["type", "title", "gridPos", "datasource", "targets"]
            for field in required:
                if field not in panel:
                    self.errors.append(f"{filepath}: Panel {panel_id} missing '{field}'")
                    valid = False

            # Validate gridPos
            if "gridPos" in panel:
                grid = panel["gridPos"]
                if not all(k in grid for k in ["x", "y", "w", "h"]):
                    self.errors.append(f"{filepath}: Panel {panel_id} has invalid gridPos")
                    valid = False

            # Validate targets
            if "targets" in panel and panel["targets"]:
                for j, target in enumerate(panel["targets"]):
                    if "expr" not in target:
                        self.warnings.append(
                            f"{filepath}: Panel {panel_id} target {j} missing 'expr'"
                        )

        return valid

    def validate_templating(self, filepath: Path, templating: Dict[str, Any]) -> bool:
        """Validate template variables."""
        if "list" not in templating:
            return True

        valid = True
        for var in templating["list"]:
            if "name" not in var:
                self.errors.append(f"{filepath}: Template variable missing 'name'")
                valid = False

            if "type" not in var:
                self.errors.append(
                    f"{filepath}: Template variable '{var.get('name', '?')}' missing 'type'"
                )
                valid = False

        return valid

    def validate_refresh_rate(self, filepath: Path, refresh: str) -> bool:
        """Validate auto-refresh is set to 30s."""
        if refresh != "30s":
            self.warnings.append(f"{filepath}: Refresh rate is '{refresh}', expected '30s'")
            return False
        return True

    def validate_time_range(self, filepath: Path, time_config: Dict[str, str]) -> bool:
        """Validate default time range is 24h."""
        if time_config.get("from") != "now-24h" or time_config.get("to") != "now":
            self.warnings.append(f"{filepath}: Time range not set to default 24h")
            return False
        return True

    def validate_dashboard(self, filepath: Path) -> bool:
        """Run all validations on a dashboard file."""
        print(f"Validating {filepath}...")

        # Check JSON syntax
        if not self.validate_json_syntax(filepath):
            return False

        # Load dashboard
        with open(filepath, "r") as f:
            data = json.load(f)

        # Run validations
        checks = [
            self.validate_dashboard_structure(filepath, data),
        ]

        if "dashboard" in data:
            dashboard = data["dashboard"]

            if "panels" in dashboard:
                checks.append(self.validate_panels(filepath, dashboard["panels"]))

            if "templating" in dashboard:
                checks.append(self.validate_templating(filepath, dashboard["templating"]))

            if "refresh" in dashboard:
                checks.append(self.validate_refresh_rate(filepath, dashboard["refresh"]))

            if "time" in dashboard:
                checks.append(self.validate_time_range(filepath, dashboard["time"]))

        return all(checks)

    def run(self) -> bool:
        """Run validation on all dashboard files."""
        if not self.dashboard_dir.exists():
            self.errors.append(f"Dashboard directory not found: {self.dashboard_dir}")
            return False

        # Find all JSON files
        json_files = list(self.dashboard_dir.rglob("*.json"))

        if not json_files:
            self.warnings.append(f"No JSON files found in {self.dashboard_dir}")
            return True

        # Validate each file
        all_valid = True
        for filepath in json_files:
            if not self.validate_dashboard(filepath):
                all_valid = False

        # Print summary
        print("\n" + "=" * 60)
        print(f"Validated {len(json_files)} dashboard(s)")

        if self.errors:
            print(f"\nERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  ❌ {error}")

        if self.warnings:
            print(f"\nWARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")

        if all_valid and not self.errors:
            print("\n✅ All dashboards are valid!")

        return all_valid and not self.errors

def main():
    """Execute the dashboard validation process."""
    # Default to infra/grafana/dashboards if no path provided
    dashboard_dir = sys.argv[1] if len(sys.argv) > 1 else "infra/grafana/dashboards"

    validator = DashboardValidator(dashboard_dir)
    success = validator.run()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
