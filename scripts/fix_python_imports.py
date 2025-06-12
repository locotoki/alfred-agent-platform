#!/usr/bin/env python3
"""Fix Python imports across the codebase.

This script scans the codebase for Python files and fixes common import issues:
1. Updates imports after module reorganization
2. Standardizes import paths
3. Fixes direct imports from the old health.py to the new health package.
"""

import os
import re
from pathlib import Path
from typing import List

# Directory to search for Python files
ROOT_DIR = Path(__file__).parent.parent
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    "cleanup-temp",
    "docs/archive",
}

# Import pattern replacements
IMPORT_REPLACEMENTS = {
    # Old health module import to new package structure
    r"from libs\.agent_core\.health import create_health_app": (
        "from libs.agent_core.health import create_health_app"
    ),
    # Fix any direct imports from the health module
    r"from libs\.agent_core import health": "from libs.agent_core.health import create_health_app",
    r"import libs\.agent_core\.health": "from libs.agent_core.health import create_health_app",
    # Fix any direct imports that might use the relocated health.py
    r"from agent_core\.health import": "from libs.agent_core.health import",
    r"import agent_core\.health": "from libs.agent_core.health import create_health_app",
}

def find_python_files() -> List[Path]:
    """Find all Python files in the codebase.

    Returns:
        List of Path objects to Python files.

    """
    python_files = []

    for root, dirs, files in os.walk(ROOT_DIR):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files

def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        True if changes were made, False otherwise.

    """
    try:
        with open(file_path, "r") as f:
            content = f.read()

        original_content = content

        # Apply all import replacements
        for pattern, replacement in IMPORT_REPLACEMENTS.items():
            content = re.sub(pattern, replacement, content)

        # Write changes if needed
        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix imports across the codebase"""
    python_files = find_python_files()
    print(f"Found {len(python_files)} Python files to check")

    changed_files = []

    for file_path in python_files:
        if fix_imports_in_file(file_path):
            changed_files.append(file_path)
            print(f"Fixed imports in {file_path}")

    print(f"\nFixed imports in {len(changed_files)} files")
    if changed_files:
        print("\nChanged files:")
        for file_path in changed_files:
            print(f"  - {file_path.relative_to(ROOT_DIR)}")

if __name__ == "__main__":
    main()
