#!/usr/bin/env python3
"""Audit Dashboard Generator - DA-006."""
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

def read_csv_file(file_path: Path) -> List[Dict[str, str]]:
    """Read a CSV file and return list of dictionaries."""
    if not file_path.exists():
        print(f"Warning: File not found: {file_path}", file=sys.stderr)
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return []

def compute_stats(deps_data, vuln_data, license_data):
    """Compute all statistics from the three data sources."""
    total_packages = len(deps_data)
    unique_packages = len(set(row.get("package", "") for row in deps_data if row.get("package")))

    location_counts = {"requirements.txt": 0, "pyproject.toml": 0, "import-only": 0, "other": 0}
    for row in deps_data:
        location = row.get("location", "")
        if ".txt" in location:
            location_counts["requirements.txt"] += 1
        elif ".toml" in location:
            location_counts["pyproject.toml"] += 1
        elif "import-only" in location:
            location_counts["import-only"] += 1
        else:
            location_counts["other"] += 1

    total_vulns = len(vuln_data)
    severity_counts = {}
    package_vuln_counts = {}
    for row in vuln_data:
        severity = row.get("severity", "unknown").lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        package = row.get("package", "")
        if package:
            package_vuln_counts[package] = package_vuln_counts.get(package, 0) + 1
    top_vulnerable = sorted(package_vuln_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    total_licenses = len(license_data)
    classification_counts = {}
    for row in license_data:
        classification = row.get("license_classification", "unknown")
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
    unknown_count = classification_counts.get("unknown", 0) + classification_counts.get("other", 0)
    unknown_ratio = (unknown_count / total_licenses * 100) if total_licenses > 0 else 0

    return {
        "deps": {"total": total_packages, "unique": unique_packages, "locations": location_counts},
        "vulns": {
            "total": total_vulns,
            "severities": severity_counts,
            "top_packages": top_vulnerable,
        },
        "licenses": {
            "total": total_licenses,
            "classifications": classification_counts,
            "unknown_count": unknown_count,
            "unknown_ratio": unknown_ratio,
        },
    }

def generate_dashboard(stats):
    """Generate the audit dashboard markdown content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    vuln_status = (
        "critical"
        if stats["vulns"]["severities"].get("critical", 0) > 0
        else "warning" if stats["vulns"]["severities"].get("high", 0) > 0 else "success"
    )
    license_status = (
        "critical"
        if stats["licenses"]["unknown_ratio"] > 50
        else "warning" if stats["licenses"]["unknown_ratio"] > 10 else "success"
    )

    repo_base = "https://github.com/locotoki/alfred-agent-platform-v2"
    badges = {
        "Dependency Inventory": f"{repo_base}/actions/workflows/deps-inventory-cron.yml",
        "Vulnerability Scan": f"{repo_base}/actions/workflows/vuln-scan-cron.yml",
        "License Scan": f"{repo_base}/actions/workflows/license-scan-cron.yml",
    }

    content = f"""# 📊 Dependency Audit Dashboard

*Last updated: {timestamp}*

## 🛡️ Status Badges

"""
    for name, url in badges.items():
        content += f"[![{name}]({url}/badge.svg)]({url})\n"

    content += f"""
![Vulnerability Status](https://img.shields.io/badge/Vulnerabilities-{stats["vulns"]["total"]}-{vuln_status})
![License Compliance](https://img.shields.io/badge/Unknown%20Licenses-{stats["licenses"]["unknown_ratio"]:.1f}%25-{license_status})

## 📈 Summary Statistics

### Dependencies
- **Total Packages**: {stats["deps"]["total"]:,}
- **Unique Packages**: {stats["deps"]["unique"]:,}
- **Requirements.txt**: {stats["deps"]["locations"]["requirements.txt"]:,}
- **Pyproject.toml**: {stats["deps"]["locations"]["pyproject.toml"]:,}
- **Import-only**: {stats["deps"]["locations"]["import-only"]:,}

### Security
- **Total Vulnerabilities**: {stats["vulns"]["total"]:,}
- **Critical**: {stats["vulns"]["severities"].get("critical", 0):,}
- **High**: {stats["vulns"]["severities"].get("high", 0):,}
- **Medium**: {stats["vulns"]["severities"].get("medium", 0):,}
- **Low**: {stats["vulns"]["severities"].get("low", 0):,}

### License Compliance
- **Total Entries**: {stats["licenses"]["total"]:,}
- **Permissive**: {stats["licenses"]["classifications"].get("permissive", 0):,}
- **Weak Copyleft**: {stats["licenses"]["classifications"].get("weak-copyleft", 0):,}
- **Copyleft**: {stats["licenses"]["classifications"].get("copyleft", 0):,}
- **Unknown/Other**: {stats["licenses"]["unknown_count"]:,} ({stats["licenses"]["unknown_ratio"]:.1f}%)

"""

    if stats["vulns"]["top_packages"]:
        content += """## 🚨 Top 10 Vulnerable Packages

| Package | Vulnerability Count |
|---------|-------------------|
"""
        for package, count in stats["vulns"]["top_packages"]:
            content += f"| {package} | {count} |\n"
        content += "\n"

    content += """## 📋 Data Sources

- **Dependency Inventory**: [`metrics/dependency_inventory.csv`](../../metrics/dependency_inventory.csv)
- **Vulnerability Report**: [`metrics/vulnerability_report.csv`](../../metrics/vulnerability_report.csv)
- **License Report**: [`metrics/license_report.csv`](../../metrics/license_report.csv)

## 🔄 Automation

This dashboard is automatically updated every Monday at 08:25 UTC via GitHub Actions.
Manual updates can be triggered by running `make audit-dashboard`.
"""
    return content

def main():
    """Generate audit dashboard from CSV reports."""
    repo_root = Path(__file__).parent.parent
    deps_data = read_csv_file(repo_root / "metrics" / "dependency_inventory.csv")
    vuln_data = read_csv_file(repo_root / "metrics" / "vulnerability_report.csv")
    license_data = read_csv_file(repo_root / "metrics" / "license_report.csv")

    stats = compute_stats(deps_data, vuln_data, license_data)
    dashboard_content = generate_dashboard(stats)

    output_file = repo_root / "docs" / "audit" / "dashboard.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(dashboard_content)

    print(f"Audit dashboard generated: {output_file}")
    print(
        f"Summary: {stats['deps']['total']:,} deps, {stats['vulns']['total']:,} vulns, {stats['licenses']['unknown_ratio']:.1f}% unknown"
    )

if __name__ == "__main__":
    main()
