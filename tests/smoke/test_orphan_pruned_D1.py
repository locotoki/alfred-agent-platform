"""Smoke test for ORPHAN slice D1 cleanup."""

import pathlib

import pytest

@pytest.mark.smoke_orphan
def test_d1_files_removed():
    """Test that all files in D1 manifest have been removed."""
    root = pathlib.Path(__file__).parents[2]
    manifest_path = root.joinpath("scripts/orphan_manifest/D1.txt")

    for line in manifest_path.read_text().splitlines():
        file_path = line.strip()
        if file_path:  # Skip empty lines
            assert not root.joinpath(file_path).exists(), f"File {file_path} should be removed"
