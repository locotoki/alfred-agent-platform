#!/usr/bin/env python3
"""
Slack CVE Alert - DA-008.

Reads vulnerability report and posts HIGH/CRITICAL CVEs to Slack #sec-alerts channel.
Only alerts for CVEs younger than 30 days or without available fixes.

Usage: python scripts/slack_cve_alert.py
Environment: SLACK_CVE_WEBHOOK (optional, fails silently if missing)
"""
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Import Alfred utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from alfred.metrics.utils.slack import (
    
,
    format_vulnerability_message,
    send_webhook_message,
)

def read_vulnerability_report(report_path: Path) -> List[Dict[str, str]]:
    """Read vulnerability report CSV and return list of vulnerabilities."""
    vulnerabilities = []
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
        return []

    return vulnerabilities

def get_cve_age_days(vuln_id: str) -> int:
    """Estimate CVE age in days based on CVE ID year."""
    if vuln_id.startswith("CVE-"):
        try:
            year_str = vuln_id.split("-")[1]
            cve_year = int(year_str)
            estimated_date = datetime(cve_year, 1, 1)
            return (datetime.now() - estimated_date).days
        except (IndexError, ValueError):
            pass
    return 0  # Unknown age, treat as new

def filter_alertable_vulnerabilities(
    vulnerabilities: List[Dict[str, str]], max_age_days: int = 30
) -> List[Dict[str, str]]:
    """Filter vulnerabilities that should trigger Slack alerts."""
    alertable = []

    for vuln in vulnerabilities:
        severity = vuln.get("severity", "unknown").lower()

        # Only alert for critical/high severity
        if severity not in ["critical", "high"]:
            continue

        vuln_id = vuln.get("vuln_id", "")
        fixed_version = vuln.get("fixed_version", "")

        # Alert if no fix available OR if CVE is young
        age_days = get_cve_age_days(vuln_id)
        no_fix = not fixed_version or fixed_version in ["", "unknown"]
        is_young = age_days <= max_age_days

        if no_fix or is_young:
            alertable.append(vuln)

    return alertable

def main():
    """Generate and send Slack CVE alerts."""
    repo_root = Path(__file__).parent.parent
    report_path = repo_root / "metrics" / "vulnerability_report.csv"

    # Read vulnerability report
    vulnerabilities = read_vulnerability_report(report_path)
    print(f"📊 Found {len(vulnerabilities)} total vulnerabilities")

    # Filter for alertable CVEs
    alertable_vulns = filter_alertable_vulnerabilities(vulnerabilities)
    print(f"🚨 Found {len(alertable_vulns)} alertable HIGH/CRITICAL CVEs")

    # Format Slack message
    message = format_vulnerability_message(alertable_vulns)

    # Get webhook URL from environment
    webhook_url = os.getenv("SLACK_CVE_WEBHOOK")
    if not webhook_url:
        print("ℹ️  SLACK_CVE_WEBHOOK not set, skipping Slack notification")
        return

    # Send to Slack
    success = send_webhook_message(message, webhook_url)
    if success:
        print(f"📤 Notified #sec-alerts of {len(alertable_vulns)} alertable vulnerabilities")
    else:
        print("❌ Failed to send Slack notification")

if __name__ == "__main__":
    main()
