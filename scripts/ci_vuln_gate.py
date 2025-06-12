#!/usr/bin/env python3
"""
CI Vulnerability Gate - DA-007/DA-008.

Parses vulnerability report CSV and fails CI if critical or high severity
vulnerabilities are found in dependencies. Supports age-based waivers.

Usage: python scripts/ci_vuln_gate.py [--max_age_days N]
Exit codes: 0 = no blocking CVEs, 1 = blocking vulnerabilities found
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

def read_vulnerability_report(report_path: Path) -> List[Dict[str, str]]:
    """Read vulnerability report CSV and return list of vulnerabilities."""
    vulnerabilities: List[Dict[str, str]] = []
    if not report_path.exists():
        print(f"Warning: Vulnerability report not found at {report_path}", file=sys.stderr)
        return vulnerabilities

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("package"):  # Skip empty rows
                    vulnerabilities.append(row)
    except Exception as e:
        print(f"Error reading vulnerability report: {e}", file=sys.stderr)
        sys.exit(1)

    return vulnerabilities

def is_vulnerability_waivable(vuln: Dict[str, str], max_age_days: int) -> bool:
    """Check if a vulnerability can be waived based on age and fix availability."""
    # Must have a fix available to be waivable
    fixed_version = vuln.get("fixed_version", "")
    if not fixed_version or fixed_version in ["", "unknown"]:
        return False

    # Check age - assume CVE ID format for published date estimation
    vuln_id = vuln.get("vuln_id", "")
    if vuln_id.startswith("CVE-"):
        try:
            # Extract year from CVE ID (e.g., CVE-2023-12345)
            year_str = vuln_id.split("-")[1]
            cve_year = int(year_str)

            # Estimate published date - use July 1st of CVE year for more realistic timing
            # CVEs are typically discovered and published throughout the year
            estimated_date = datetime(cve_year, 7, 1)
            age_days = (datetime.now() - estimated_date).days

            return age_days > max_age_days
        except (IndexError, ValueError):
            # If we can't parse CVE year, don't waive
            return False

    return False

def analyze_vulnerabilities(
    vulnerabilities: List[Dict[str, str]], max_age_days: int
) -> Dict[str, Any]:
    """Analyze vulnerabilities by severity and age, return counts and blocking list."""
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    blocking_vulns = []
    waived_vulns = []

    for vuln in vulnerabilities:
        severity = vuln.get("severity", "unknown").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1
        else:
            severity_counts["unknown"] += 1

        # Check if this is a blocking vulnerability (critical or high)
        if severity in ["critical", "high"]:
            if is_vulnerability_waivable(vuln, max_age_days):
                waived_vulns.append(vuln)
            else:
                blocking_vulns.append(vuln)

    return {
        "severity_counts": severity_counts,
        "blocking_vulns": blocking_vulns,
        "waived_vulns": waived_vulns,
        "total_count": len(vulnerabilities),
    }

def print_vulnerability_summary(analysis: Dict[str, Any], max_age_days: int):
    """Print a formatted vulnerability summary."""
    print("🔍 Vulnerability Scan Results")
    print("=" * 40)
    print(f"Total vulnerabilities found: {analysis['total_count']}")
    print()

    if analysis["total_count"] == 0:
        print("✅ No vulnerabilities detected in dependencies")
        return

    print("Breakdown by severity:")
    for severity, count in analysis["severity_counts"].items():
        if count > 0:
            emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
                "unknown": "⚪",
            }.get(severity, "⚪")
            print(f"  {emoji} {severity.upper()}: {count}")

    # Show waived vulnerabilities
    if analysis["waived_vulns"]:
        print(f"\n🕒 WAIVED vulnerabilities (age > {max_age_days} days, fix available):")
        for vuln in analysis["waived_vulns"]:
            package = vuln.get("package", "unknown")
            vuln_id = vuln.get("vuln_id", "unknown")
            severity = vuln.get("severity", "unknown").upper()
            fixed_version = vuln.get("fixed_version", "unknown")
            print(f"  • {package}: {vuln_id} ({severity}) - fix: {fixed_version}")

def main() -> None:
    """Run the CI vulnerability gate check."""
    parser = argparse.ArgumentParser(description="CI vulnerability gate with age-based waivers")
    parser.add_argument(
        "--max_age_days",
        type=int,
        default=30,
        help="Maximum age in days for waiving critical/high CVEs with fixes (default: 30)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    report_path = repo_root / "metrics" / "vulnerability_report.csv"

    # Read vulnerability report
    vulnerabilities = read_vulnerability_report(report_path)

    # Analyze with age-based waivers
    analysis = analyze_vulnerabilities(vulnerabilities, args.max_age_days)

    # Print summary
    print_vulnerability_summary(analysis, args.max_age_days)

    # Check for blocking vulnerabilities
    blocking_count = len(analysis["blocking_vulns"])

    if blocking_count > 0:
        print()
        print("❌ CI GATE FAILURE")
        print(f"Found {blocking_count} blocking critical/high severity vulnerabilities")
        print("🛡️  Action required: Update vulnerable dependencies before merging")
        print()

        print("Blocking vulnerabilities:")
        for vuln in analysis["blocking_vulns"]:
            package = vuln.get("package", "unknown")
            vuln_id = vuln.get("vuln_id", "unknown")
            severity = vuln.get("severity", "unknown").upper()
            fixed_version = vuln.get("fixed_version", "unknown")
            print(f"  • {package}: {vuln_id} ({severity}) - fix: {fixed_version}")

        sys.exit(1)

    print()
    print("✅ CI GATE PASSED")
    if analysis["waived_vulns"]:
        print(
            f"No blocking vulnerabilities (waived {len(analysis['waived_vulns'])} old CVEs with fixes)"
        )
    else:
        print("No critical or high severity vulnerabilities found")
    sys.exit(0)

if __name__ == "__main__":
    main()
