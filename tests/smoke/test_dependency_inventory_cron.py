"""
Smoke tests for dependency inventory cron workflow - DA-002.

Tests that the GitHub Actions workflow for weekly dependency inventory
refresh exists and is properly configured.
"""

from pathlib import Path

import pytest

def test_deps_inventory_cron_workflow_exists():
    """Test that the dependency inventory cron workflow file exists."""
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "deps-inventory-cron.yml"

    assert workflow_path.exists(), "deps-inventory-cron.yml workflow should exist"

def test_deps_inventory_cron_workflow_content():
    """Test that the workflow has expected content."""
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "deps-inventory-cron.yml"

    if not workflow_path.exists():
        pytest.skip("deps-inventory-cron.yml does not exist")

    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check for required elements
    assert "schedule:" in content, "Workflow should have schedule trigger"
    assert "cron:" in content, "Workflow should have cron schedule"
    assert "workflow_dispatch:" in content, "Workflow should have manual dispatch"
    assert "make deps-inventory" in content, "Workflow should run deps-inventory command"
    assert "github-actions[bot]" in content, "Workflow should use bot user for commits"

def test_deps_inventory_cron_workflow_yaml_valid():
    """Test that the workflow YAML is valid."""
    repo_root = Path(__file__).parent.parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "deps-inventory-cron.yml"

    if not workflow_path.exists():
        pytest.skip("deps-inventory-cron.yml does not exist")

    try:
        import yaml
        with open(workflow_path, "r", encoding="utf-8") as f:
            yaml.safe_load(f)
    except ImportError:
        pytest.skip("PyYAML not available for validation")
    except yaml.YAMLError as e:
        pytest.fail(f"Workflow YAML is invalid: {e}")
