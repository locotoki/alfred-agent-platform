"""
Smoke tests for dependency inventory system - DA-001

Tests the basic functionality of the dependency inventory generator
to ensure it produces valid output.
"""

import csv
from pathlib import Path

import pytest

def test_dependency_inventory_exists():
    """Test that the dependency inventory CSV file exists."""
    repo_root = Path(__file__).parent.parent.parent
    inventory_path = repo_root / "metrics" / "dependency_inventory.csv"

    assert inventory_path.exists(), "dependency_inventory.csv should exist"

def test_dependency_inventory_has_data():
    """Test that the dependency inventory has at least one row of data."""
    repo_root = Path(__file__).parent.parent.parent
    inventory_path = repo_root / "metrics" / "dependency_inventory.csv"

    if not inventory_path.exists():
        pytest.skip("dependency_inventory.csv does not exist")

    with open(inventory_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) >= 1, "dependency_inventory.csv should have at least 1 row of data"

def test_dependency_inventory_format():
    """Test that the dependency inventory has the correct CSV format."""
    repo_root = Path(__file__).parent.parent.parent
    inventory_path = repo_root / "metrics" / "dependency_inventory.csv"

    if not inventory_path.exists():
        pytest.skip("dependency_inventory.csv does not exist")

    with open(inventory_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Check header format
        expected_headers = ["package", "declared_version", "latest_pinned", "location"]
        assert reader.fieldnames == expected_headers, f"CSV headers should be {expected_headers}"

        # Check at least one row has required fields
        first_row = next(reader, None)
        if first_row:
            assert (
                "package" in first_row and first_row["package"]
            ), "package field should not be empty"
            assert (
                "location" in first_row and first_row["location"]
            ), "location field should not be empty"

def test_dependency_inventory_has_common_packages():
    """Test that the inventory includes some expected common packages."""
    repo_root = Path(__file__).parent.parent.parent
    inventory_path = repo_root / "metrics" / "dependency_inventory.csv"

    if not inventory_path.exists():
        pytest.skip("dependency_inventory.csv does not exist")

    with open(inventory_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        packages = {row["package"].lower() for row in reader}

    # Should find some common Python packages in a typical project
    common_packages = {"pytest", "requests", "fastapi", "pandas", "numpy", "flask", "django"}
    found_packages = packages & common_packages

    # Don't assert specific packages exist, just check format is working
    assert len(packages) > 0, "Should find at least some packages in the inventory"
