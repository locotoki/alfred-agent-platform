#!/usr/bin/env python3
"""
Find orphan script candidates for SC-250 Phase C-2.

Scans for scripts that are not referenced anywhere in the repository
using git grep and marks them as potential orphans.
"""

import csv
import pathlib
import subprocess

EXT = {".sh", ".py", ".ps1"}
def main():
    """Find and list orphan script candidates."""
    # Find all script files
    paths = [p for p in pathlib.Path(".").rglob("*") if p.suffix in EXT]

    # Find which scripts are referenced somewhere (use basename for faster search)
    used = set()
    for p in paths:
        # Use basename for git grep to find references more efficiently
        basename = p.name
        try:
            out = subprocess.run(
                ["git", "grep", "-l", basename], capture_output=True, text=True, timeout=5
            ).stdout
            if out.strip():
                used.add(str(p))
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # File not found in git grep or timeout, continue
            pass

    # Read current inventory
    with open("metrics/scripts_inventory.csv") as f:
        rows = list(csv.DictReader(f))

    # Print orphan candidates
    for r in rows:
        if r["status"] == "UNKNOWN" and r["path"] not in used:
            print(r["path"])

if __name__ == "__main__":
    main()
