#!/usr/bin/env python3
"""
Generate scripts inventory for the alfred-agent-platform-v2 repository.

Scans the repository for script files and outputs a CSV with path, extension, and size.
Part of Spring-Clean Initiative SC-250 Phase C-0.
"""

import csv
import sys
from pathlib import Path
from typing import Iterator, Tuple

# Script extensions to scan for
SCRIPT_EXTENSIONS = {".sh", ".py", ".ps1", ".js", ".ts"}
# Directories to skip during scan
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".env",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Patterns for backup directories
BACKUP_PATTERNS = {"backup", "backup-", "backup_"}

def should_skip_directory(dir_path: Path) -> bool:
    """Check if directory should be skipped during scan."""
    dir_name = dir_path.name.lower()

    # Skip exact matches
    if dir_name in SKIP_DIRS:
        return True

    # Skip backup directories
    for pattern in BACKUP_PATTERNS:
        if dir_name.startswith(pattern):
            return True

    return False

def find_script_files(root_path: Path) -> Iterator[Tuple[str, str, int]]:
    """
    Recursively find script files in the repository.

    Yields:
        Tuple of (relative_path, extension, size_bytes)
    """
    for item in root_path.rglob("*"):
        try:
            # Skip directories
            if item.is_dir():
                continue

            # Check if any parent directory should be skipped
            if any(should_skip_directory(parent) for parent in item.parents):
                continue

            # Check if file has a script extension
            if item.suffix.lower() not in SCRIPT_EXTENSIONS:
                continue

            # Get file size
            try:
                size_bytes = item.stat().st_size
            except (OSError, IOError) as e:
                print(f"Warning: Could not get size for {item}: {e}", file=sys.stderr)
                continue

            # Get relative path from repository root
            try:
                rel_path = item.relative_to(root_path)
            except ValueError:
                # File is outside repository root, skip
                continue

            yield (str(rel_path), item.suffix.lower(), size_bytes)

        except (OSError, IOError) as e:
            print(f"Warning: Error processing {item}: {e}", file=sys.stderr)
            continue

def main() -> None:
    """Generate and output scripts inventory CSV."""
    # Find repository root (assume script is in repo/scripts/)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    if not repo_root.exists():
        print(f"Error: Repository root not found at {repo_root}", file=sys.stderr)
        sys.exit(1)

    # Load existing CSV if present to preserve manual annotations
    status_map = {}
    existing = repo_root / "metrics" / "scripts_inventory.csv"
    if existing.exists():
        with existing.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                status_map[row["path"]] = row.get("status", "UNKNOWN")

    # Collect script files
    script_files = list(find_script_files(repo_root))

    # Sort by path alphabetically
    script_files.sort(key=lambda x: x[0])

    # Output CSV to stdout
    writer = csv.writer(sys.stdout)
    writer.writerow(["path", "ext", "size_bytes", "status"])

    for path, ext, size in script_files:
        p = repo_root / path
        if p.exists():  # ignore files already deleted (ORPHAN pruned)
            status = status_map.get(path, "UNKNOWN")
            writer.writerow([path, ext, size, status])

if __name__ == "__main__":
    main()
