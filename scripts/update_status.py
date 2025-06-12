#!/usr/bin/env python3
"""Status Beacon Updater for SC-241 Agent Consolidation.

This script queries GitHub API to count closed vs total issues with the label
epic:SC-241 and updates status.json in the repo root with current progress.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Repository root is parent of scripts directory
REPO_ROOT = Path(__file__).parent.parent
STATUS_FILE = REPO_ROOT / "status.json"

def run_gh_command(command):
    """Run a GitHub CLI command and return its JSON output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(command)}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)

def get_current_branch():
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

def get_last_green_sha():
    """Get the last commit SHA that passed CI."""
    try:
        # Try to get the last successful workflow run's HEAD SHA
        result = run_gh_command(
            [
                "gh",
                "run",
                "list",
                "--workflow=ci.yml",
                "--status=success",
                "--json=headSha",
                "--limit=1",
            ]
        )
        if result and len(result) > 0:
            return result[0]["headSha"]
    except Exception as e:
        print(f"Warning: Could not fetch last green SHA: {e}")

    # Fallback - use current SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()

def get_issue_counts():
    """Get counts of closed and total issues with label epic:SC-241."""
    # Get all issues with the epic:SC-241 label
    issues = run_gh_command(
        [
            "gh",
            "issue",
            "list",
            "--label",
            "epic:SC-241",
            "--state",
            "all",
            "--json",
            "state",
            "--limit",
            "1000",  # Assuming we won't have more than 1000 issues
        ]
    )

    total = len(issues)
    closed = sum(1 for issue in issues if issue["state"] == "closed")

    return {"tasks_done": closed, "tasks_total": total}

def update_status_file():
    """Update the status.json file with current progress."""
    # Ensure status file exists with default values
    if not STATUS_FILE.exists():
        status = {
            "branch": "ops/SC-241-agent-consolidation",
            "last_green_sha": "",
            "phase_complete": False,
            "tasks_done": 0,
            "tasks_total": 0,
            "updated": datetime.utcnow().isoformat(),
        }
    else:
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)

    # Update with current values
    issue_counts = get_issue_counts()
    status.update(
        {
            "branch": get_current_branch(),
            "last_green_sha": get_last_green_sha(),
            "tasks_done": issue_counts["tasks_done"],
            "tasks_total": issue_counts["tasks_total"],
            "phase_complete": issue_counts["tasks_done"] == issue_counts["tasks_total"]
            and issue_counts["tasks_total"] > 0,
            "updated": datetime.utcnow().isoformat(),
        }
    )

    # Write updated status
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)

    print(f"Updated status.json: {status['tasks_done']}/{status['tasks_total']} tasks complete")
    return status

if __name__ == "__main__":
    update_status_file()
