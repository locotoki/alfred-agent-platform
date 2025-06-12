"""Smoke tests for Slack CVE alert system - DA-008."""

import csv
import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

@pytest.mark.parametrize(
    "file_path,description",
    [
        ("scripts/slack_cve_alert.py", "Slack CVE alert script"),
        (".github/workflows/cve-alert-weekly.yml", "CVE alert weekly workflow"),
    ],
)
def test_required_files_exist(file_path, description):
    """Test that required files exist."""
    repo_root = Path(__file__).parent.parent.parent
    assert (repo_root / file_path).exists(), f"{description} should exist"

def test_slack_alert_can_import():
    """Test that the Slack alert script can be imported without errors."""
    repo_root = Path(__file__).parent.parent.parent

    result = subprocess.run(
        ["python3", "-c", "import sys; sys.path.append('scripts'); import slack_cve_alert"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Import failed: {result.stderr}"

def test_slack_alert_no_webhook_graceful_failure():
    """Test that Slack alert fails gracefully when no webhook URL is provided."""
    repo_root = Path(__file__).parent.parent.parent

    # Create test vulnerability data with HIGH/CRITICAL CVEs
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["package", "installed_version", "vuln_id", "severity", "fixed_version"])
        # Young HIGH CVE (should trigger alert)
        writer.writerow(["test-package", "1.0.0", "CVE-2024-12345", "high", "1.0.1"])
        temp_report = f.name

    try:
        original_report = repo_root / "metrics" / "vulnerability_report.csv"
        backup_exists = original_report.exists()
        if backup_exists:
            backup_content = original_report.read_text()

        original_report.write_text(Path(temp_report).read_text())

        # Run without SLACK_CVE_WEBHOOK env var
        env = os.environ.copy()
        env.pop("SLACK_CVE_WEBHOOK", None)

        result = subprocess.run(
            ["python3", "scripts/slack_cve_alert.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )

        # Should exit with code 0 (graceful failure)
        assert result.returncode == 0
        assert "SLACK_CVE_WEBHOOK not set" in result.stdout

    finally:
        if backup_exists:
            original_report.write_text(backup_content)
        Path(temp_report).unlink(missing_ok=True)

def test_slack_alert_filters_low_medium_vulnerabilities():
    """Test that Slack alert only processes HIGH/CRITICAL vulnerabilities."""
    repo_root = Path(__file__).parent.parent.parent

    # Create test vulnerability data with mixed severities
    with NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["package", "installed_version", "vuln_id", "severity", "fixed_version"])
        writer.writerow(["pkg1", "1.0.0", "CVE-2025-11111", "low", "1.0.1"])
        writer.writerow(["pkg2", "1.0.0", "CVE-2025-22222", "medium", "1.0.1"])
        writer.writerow(["pkg3", "1.0.0", "CVE-2025-33333", "high", "1.0.1"])
        writer.writerow(["pkg4", "1.0.0", "CVE-2025-44444", "critical", ""])
        temp_report = f.name

    try:
        original_report = repo_root / "metrics" / "vulnerability_report.csv"
        backup_exists = original_report.exists()
        if backup_exists:
            backup_content = original_report.read_text()

        original_report.write_text(Path(temp_report).read_text())

        # Run without webhook (graceful failure mode to test filtering)
        env = os.environ.copy()
        env.pop("SLACK_CVE_WEBHOOK", None)

        result = subprocess.run(
            ["python3", "scripts/slack_cve_alert.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        # Should only mention 1 alertable CVE (the CRITICAL with no fix)
        # The HIGH CVE with fix is young so not alertable
        assert "1 alertable HIGH/CRITICAL CVEs" in result.stdout

    finally:
        if backup_exists:
            original_report.write_text(backup_content)
        Path(temp_report).unlink(missing_ok=True)

@pytest.mark.parametrize(
    "expected_content",
    [
        "name: CVE Alert Weekly",
        "schedule:",
        "cron: '30 8 * * 1'",  # Monday 08:30 UTC
        "workflow_dispatch:",
        "make vuln-scan",
        "python scripts/slack_cve_alert.py",
        "SLACK_CVE_WEBHOOK",
    ],
)
def test_slack_alert_workflow_content(expected_content):
    """Test that CVE alert workflow contains expected content."""
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "cve-alert-weekly.yml"

    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert expected_content in content

def test_makefile_cve_alert_target():
    """Test that Makefile has cve-alert target."""
    repo_root = Path(__file__).parent.parent.parent
    makefile_path = repo_root / "Makefile"
    assert makefile_path.exists()

    with open(makefile_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "cve-alert:" in content
    assert "python3 scripts/slack_cve_alert.py" in content
    assert "cve-alert" in content  # Should be in .PHONY and help text
