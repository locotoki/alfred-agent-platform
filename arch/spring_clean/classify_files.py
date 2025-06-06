#!/usr/bin/env python3
"""
Classify repository files according to Spring-Clean rules.

This script takes the raw_file_list.txt generated by scripts_inventory.sh
and classifies each file as USED or ORPHAN based on predefined rules.
"""

import csv
import os
import re
from pathlib import Path


def classify_file(file_path: str) -> str:
    """
    Classify a file as USED or ORPHAN based on predefined rules.

    Args:
        file_path: Path to the file to classify

    Returns:
        str: "USED" or "ORPHAN"
    """
    # Define patterns
    orphan_patterns = [
        r"^backup/",
        r"^cleanup-temp/",
        r"\.bak$",
        r"\.bak-\d+",
        r"\.backup$",
        r"\.old$",
        r"\.original$",
        r"\.tmp$",
        r"\.temp$",
        r"-backup/",
        r"-backup$",
        r"-20\d{6}",  # Date patterns like -20250514
    ]

    # Specific directories we consider ORPHAN
    orphan_directories = [
        "backup",
        "backup-tmp",
        "cleanup-temp",
    ]

    # Specific extensions that indicate ORPHAN files
    orphan_extensions = [
        ".bak",
        ".backup",
        ".old",
        ".original",
        ".tmp",
        ".temp",
    ]

    # Check if the path matches any orphan pattern
    for pattern in orphan_patterns:
        if re.search(pattern, file_path):
            return "ORPHAN"

    # Check if in orphan directories
    if any(file_path.startswith(d + "/") for d in orphan_directories):
        return "ORPHAN"

    # Check extensions
    _, ext = os.path.splitext(file_path)
    if ext in orphan_extensions:
        return "ORPHAN"

    # Classify remaining files by directory
    if file_path.startswith("alfred/"):
        return "USED"  # Core framework

    if file_path.startswith(".github/workflows/"):
        return "USED"  # CI/CD

    if file_path.startswith("docs/") or file_path.startswith("arch/"):
        return "USED"  # Documentation

    if file_path.startswith("scripts/"):
        return "USED"  # Scripts

    if file_path.startswith("tests/"):
        return "USED"  # Tests

    if file_path.startswith("charts/"):
        return "USED"  # Helm charts

    if file_path.startswith("services/"):
        # Consider active services USED, but check for backup/old indicators
        if any(
            indicator in file_path
            for indicator in [".bak", ".old", ".backup", "mission-control.old"]
        ):
            return "ORPHAN"
        return "USED"

    # Root level configuration files
    if file_path in [
        ".dockerignore",
        ".gitignore",
        ".flake8",
        ".pre-commit-config.yaml",
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "docker-compose-clean.yml",
        "pyproject.toml",
        "setup.py",
        "Makefile",
        "requirements.txt",
        "pytest.ini",
        "mypy.ini",
        "README.md",
        "VERSION",
        "LICENSE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CLAUDE.md",
    ]:
        return "USED"

    # Root level temporary files
    if file_path.endswith((".md", ".txt", ".sh")) and file_path.lower() not in [
        "readme.md",
        "license",
        "contributing.md",
        "security.md",
        "setup.sh",
        "start-platform.sh",
    ]:
        return "ORPHAN"

    # Default - mark remaining files as USED to be on the safe side
    return "USED"


def main() -> None:
    """Process raw_file_list.txt and generate inventory.csv with classifications."""
    # Get the directory of this script
    script_dir = Path(__file__).parent

    # Input and output files
    input_file = script_dir / "raw_file_list.txt"
    output_file = script_dir / "inventory.csv"

    if not input_file.exists():
        print(f"Error: {input_file} not found. Run scripts_inventory.sh first.")
        return

    # Read the list of files
    with open(input_file, "r") as f:
        file_list = [line.strip() for line in f if line.strip()]

    # Classify each file
    classifications = []
    for file_path in file_list:
        file_path = file_path.strip('"\\')  # Clean up quotes and backslashes
        classification = classify_file(file_path)
        classifications.append((file_path, classification))

    # Write to CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file_path", "classification"])
        writer.writerows(classifications)

    # Generate counts
    used_count = sum(1 for _, classification in classifications if classification == "USED")
    orphan_count = sum(1 for _, classification in classifications if classification == "ORPHAN")
    total_count = len(classifications)

    print("Classification complete:")
    print(f"  - Total files: {total_count}")
    print(f"  - USED:       {used_count} ({used_count/total_count*100:.1f}%)")
    print(f"  - ORPHAN:     {orphan_count} ({orphan_count/total_count*100:.1f}%)")
    print(f"Results written to {output_file}")


if __name__ == "__main__":  # pragma: no cover
    main()
