#!/usr/bin/env python3
"""
Script to fix the decorator ordering in test files for SC-320.

This script fixes the order of pytest decorators to ensure they are correctly formatted.
"""

import re
from pathlib import Path

def fix_youtube_workflows(file_path):
    """Fix the decorator ordering in YouTube workflow tests."""
    with open(file_path, "r") as f:
        content = f.read()

    # Fix the async and xfail decorator order (async should be after xfail)
    pattern = r'async @pytest\.mark\.xfail\(reason="([^"]+)", strict=False\)'
    replacement = r'@pytest.mark.xfail(reason="\1", strict=False)\nasync'

    modified_content = re.sub(pattern, replacement, content)

    with open(file_path, "w") as f:
        f.write(modified_content)

    print(f"Fixed decorator ordering in {file_path}")

def fix_class_method_decorators(file_path):
    """Fix the decorator ordering for class methods."""
    with open(file_path, "r") as f:
        content = f.read()

    # Find indentation level for method decorator
    class_def_match = re.search(r"class\s+\w+.*?:", content)
    if not class_def_match:
        print(f"No class definition found in {file_path}")
        return

    # Look for class methods with xfail decorators directly under the method name without indentation
    pattern = r"(    @pytest\.mark\.xfail.*?\n)(\s*)def (test_\w+)"

    matches = re.findall(pattern, content)
    if not matches:
        print(f"No incorrectly formatted method decorators found in {file_path}")
        return

    # Fix each match by adding proper indentation to the method
    for decorator, indentation, method_name in matches:
        # Ensure decorator has correct indentation (should be 4 spaces more than method)
        if len(indentation) < 4:
            old_pattern = f"{decorator}{indentation}def {method_name}"
            new_pattern = f"{decorator}    def {method_name}"
            content = content.replace(old_pattern, new_pattern)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"Fixed class method decorators in {file_path}")

def main():
    """Fix decorator order issues in test files."""
    project_root = Path(__file__).parent.parent

    # Fix YouTube workflows
    youtube_file = project_root / "tests" / "test_youtube_workflows.py"
    if youtube_file.exists():
        fix_youtube_workflows(youtube_file)

    # Fix class method decorators in alfred/ml/test_hf_embedder.py
    hf_file = project_root / "tests" / "alfred" / "ml" / "test_hf_embedder.py"
    if hf_file.exists():
        fix_class_method_decorators(hf_file)

    # Fix class method decorators in backend/ml/test_faiss_index.py
    faiss_file = project_root / "tests" / "backend" / "ml" / "test_faiss_index.py"
    if faiss_file.exists():
        fix_class_method_decorators(faiss_file)

if __name__ == "__main__":
    main()
