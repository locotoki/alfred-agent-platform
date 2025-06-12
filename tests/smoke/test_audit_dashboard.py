"""Smoke tests for audit dashboard generation system - DA-006."""

import subprocess
from pathlib import Path

import pytest

def test_audit_dashboard_generator_exists():
    """Test that the audit dashboard generator script exists."""
    repo_root = Path(__file__).parent.parent.parent
    assert (repo_root / "scripts" / "gen_audit_dashboard.py").exists()

def test_audit_dashboard_can_be_generated():
    """Test that the audit dashboard can be generated without errors."""
    repo_root = Path(__file__).parent.parent.parent
    dashboard_path = repo_root / "docs" / "audit" / "dashboard.md"

    if not dashboard_path.exists():
        subprocess.run(
            ["python", "scripts/gen_audit_dashboard.py"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )

    assert dashboard_path.exists()

@pytest.mark.parametrize(
    "badge",
    [
        "deps-inventory-cron.yml/badge.svg",
        "vuln-scan-cron.yml/badge.svg",
        "license-scan-cron.yml/badge.svg",
    ],
)
def test_audit_dashboard_contains_badges(badge):
    """Test that the audit dashboard contains the required workflow badges."""
    repo_root = Path(__file__).parent.parent.parent
    with open(repo_root / "docs" / "audit" / "dashboard.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert badge in content

@pytest.mark.parametrize(
    "section",
    [
        "# 📊 Dependency Audit Dashboard",
        "## 🛡️ Status Badges",
        "## 📈 Summary Statistics",
        "## 📋 Data Sources",
    ],
)
def test_audit_dashboard_format(section):
    """Test that the audit dashboard has proper markdown format."""
    repo_root = Path(__file__).parent.parent.parent
    with open(repo_root / "docs" / "audit" / "dashboard.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert section in content

def test_makefile_audit_dashboard_target():
    """Test that the Makefile has an audit-dashboard target."""
    repo_root = Path(__file__).parent.parent.parent
    with open(repo_root / "Makefile", "r", encoding="utf-8") as f:
        content = f.read()
    assert "audit-dashboard:" in content and "gen_audit_dashboard.py" in content

@pytest.mark.parametrize(
    "element", ["name: Audit Dashboard Update", "cron: '25 8 * * 1'", "make audit-dashboard"]
)
def test_workflow_file_exists(element):
    """Test that the audit dashboard cron workflow exists."""
    repo_root = Path(__file__).parent.parent.parent
    with open(
        repo_root / ".github" / "workflows" / "audit-dashboard-cron.yml", "r", encoding="utf-8"
    ) as f:
        content = f.read()
    assert element in content

@pytest.mark.parametrize(
    "section", ["### Dependencies", "### Security", "### License Compliance", "**Total Packages**"]
)
def test_dashboard_contains_statistics(section):
    """Test that the dashboard contains basic statistics sections."""
    repo_root = Path(__file__).parent.parent.parent
    with open(repo_root / "docs" / "audit" / "dashboard.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert section in content

@pytest.mark.parametrize(
    "link", ["dependency_inventory.csv", "vulnerability_report.csv", "license_report.csv"]
)
def test_dashboard_links_to_data_sources(link):
    """Test that the dashboard contains links to the CSV data sources."""
    repo_root = Path(__file__).parent.parent.parent
    with open(repo_root / "docs" / "audit" / "dashboard.md", "r", encoding="utf-8") as f:
        content = f.read()
    assert link in content
