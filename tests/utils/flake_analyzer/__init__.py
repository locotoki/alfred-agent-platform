"""
Flake detector implementation (#651).
Parses pytest JSON output and emits GitHub summary for flaky tests.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

def analyze(json_path: str) -> Dict[str, List[str]]:
    """Analyze pytest JSON report for flaky tests.

    Args:
        json_path: Path to pytest JSON output file

    Returns:
        Dict with flake analysis results including flaky test list
    """
    if not os.path.exists(json_path):
        return {"flakes": [], "error": f"JSON report not found: {json_path}"}

    try:
        with open(json_path, "r") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        return {"flakes": [], "error": f"Invalid JSON: {e}"}

    # Extract test results
    tests = report.get("tests", [])
    failed_tests = [test for test in tests if test.get("outcome") == "failed"]

    # For now, consider any failed test as potentially flaky
    # In a real implementation, this would compare across multiple runs
    flaky_tests = [
        f"{test.get('nodeid', 'unknown')}: {test.get('call', {}).get('longrepr', 'No details')}"
        for test in failed_tests
    ]

    return {
        "flakes": flaky_tests,
        "total_tests": len(tests),
        "failed_tests": len(failed_tests),
        "summary": generate_github_summary(flaky_tests, len(tests), len(failed_tests)),
    }

def generate_github_summary(flaky_tests: List[str], total_tests: int, failed_tests: int) -> str:
    """Generate GitHub Actions summary table for flaky tests.

    Args:
        flaky_tests: List of flaky test descriptions
        total_tests: Total number of tests run
        failed_tests: Number of failed tests

    Returns:
        GitHub Actions summary markdown content
    """
    if not flaky_tests:
        return f"""## ✅ Flake Detection Results

| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| Failed Tests | {failed_tests} |
| Flaky Tests | 0 |

**Status**: No flaky tests detected! 🎉
"""

    flaky_table_rows = []
    for i, test in enumerate(flaky_tests[:10], 1):  # Limit to first 10
        # Extract test name and error
        if ": " in test:
            test_name, error = test.split(": ", 1)
            # Truncate long error messages
            if len(error) > 100:
                error = error[:97] + "..."
        else:
            test_name, error = test, "No details"

        flaky_table_rows.append(f"| {i} | `{test_name}` | {error} |")

    summary = f"""## ⚠️ Flake Detection Results

| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| Failed Tests | {failed_tests} |
| Flaky Tests | {len(flaky_tests)} |

### Flaky Tests Detected

| # | Test | Error |
|---|------|-------|
{"".join(flaky_table_rows)}

"""

    if len(flaky_tests) > 10:
        summary += f"\n*({len(flaky_tests) - 10} additional flaky tests truncated)*\n"

    return summary

def emit_github_summary(analysis_result: Dict[str, List[str]]) -> None:
    """Emit GitHub Actions summary if running in CI.

    Args:
        analysis_result: Result from analyze() function
    """
    if "GITHUB_STEP_SUMMARY" not in os.environ:
        print("Not running in GitHub Actions, skipping summary emission")
        return

    summary_file = os.environ["GITHUB_STEP_SUMMARY"]
    summary_content = analysis_result.get("summary", "No summary available")

    try:
        with open(summary_file, "a") as f:
            f.write(summary_content)
        print(f"✅ GitHub summary written to {summary_file}")
    except Exception as e:
        print(f"❌ Failed to write GitHub summary: {e}")
