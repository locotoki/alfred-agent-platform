#!/usr/bin/env python3
"""Licence gate compliance checker for Alfred."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import structlog

logger = structlog.get_logger(__name__)
ALLOWED_LICENCES = {
    "Apache-2.0",
    "Apache Software License",
    "MIT",
    "MIT License",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "BSD License",
    "BSD",
    "ISC License",
    "Python Software Foundation License",
}

LICENCE_ALIASES = {
    "Apache Software License": "Apache-2.0",
    "MIT License": "MIT",
    "BSD License": "BSD",
    "ISC License": "ISC",
    "Python Software Foundation License": "PSF-2.0",
}

SAFE_UNKNOWN = {"urllib3"}  # allowed packages with UNKNOWN licence


def _normalise(lic: str) -> List[str]:
    """Split composite licence strings and normalize."""
    # Handle licences with embedded copyright text first
    if lic.startswith("MIT License\n") and "Copyright" in lic:
        return ["MIT License"]
    # split on common delimiters ';' ',' and strip
    parts = [p.strip() for p in re.split(r"[;,]", lic)]
    # map UNKNOWN to placeholder
    return ["UNKNOWN" if p.upper() == "UNKNOWN" else p for p in parts if p]


def normalize_licence(licence: str) -> str:
    """Normalize licence name to canonical form."""
    # Handle licences with full text
    if licence.startswith("MIT License\n"):
        return "MIT License"

    return LICENCE_ALIASES.get(licence, licence)


def get_package_licences() -> List[Dict[str, str]]:
    """Extract licence information using pip-licenses."""
    try:
        result = subprocess.run(
            ["pip-licenses", "--format=json", "--with-urls"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to run pip-licenses", error=str(e))
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse pip-licenses output", error=str(e))
        sys.exit(1)


def load_licence_waivers() -> Set[str]:
    """Load waived packages from .licence_waivers file."""
    waiver_file = Path(".licence_waivers")
    waivers = set()
    if waiver_file.exists():
        for line in waiver_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                waivers.add(line)
    return waivers


def create_github_annotation(message: str, level: str = "error") -> None:
    """Create GitHub annotation for CI visibility."""
    if os.getenv("GITHUB_ACTIONS"):
        print(f"::{level}::{message}")


def emit_compliance_metrics(disallowed_packages: List[Tuple[str, str]]) -> None:
    """Emit Prometheus metrics for licence compliance."""
    try:
        from alfred.metrics.compliance import record_licence_violations

        for package, licence in disallowed_packages:
            record_licence_violations(package, licence)
    except ImportError:
        logger.warning("Metrics module not available")


def validate_licences() -> Tuple[bool, List[Tuple[str, str]]]:
    """Validate all dependencies against allowed licences."""
    packages = get_package_licences()
    waivers = load_licence_waivers()
    violations = []

    logger.info("Starting licence validation", total_packages=len(packages))

    for pkg in packages:
        name = pkg.get("Name", "unknown")
        raw_licence = pkg.get("License", "unknown")

        # Use new normalise function to handle composite licences
        licence_parts = _normalise(raw_licence)

        # Check each part of composite licence
        is_allowed = True
        for lic_part in licence_parts:
            normalized = normalize_licence(lic_part)

            # Special handling for UNKNOWN packages in safe list
            if normalized == "UNKNOWN" and name in SAFE_UNKNOWN:
                continue

            if normalized not in ALLOWED_LICENCES:
                waiver_key = f"{name}=={raw_licence}"
                if waiver_key not in waivers:
                    is_allowed = False
                    break

        if not is_allowed:
            violations.append((name, raw_licence))
            logger.warning("Disallowed licence", package=name, licence=raw_licence)

    logger.info("Validation complete", violations=len(violations))
    emit_compliance_metrics(violations)
    return len(violations) == 0, violations


def main() -> None:
    """Run licence gate validation."""
    logger.info("Alfred licence gate starting")
    is_compliant, violations = validate_licences()

    if violations:
        violation_list = "\n".join(f"  - {pkg}: {licence}" for pkg, licence in violations)
        message = f"Licence gate failed! {len(violations)} disallowed licences:\n{violation_list}"
        create_github_annotation(message)

        print("\n❌ LICENCE GATE FAILED", file=sys.stderr)
        print(f"Found {len(violations)} disallowed licences:", file=sys.stderr)
        for package, licence in violations:
            print(f"  {package}: {licence}", file=sys.stderr)

        print("\nTo waive, add to .licence_waivers:", file=sys.stderr)
        for package, licence in violations:
            print(f"  {package}=={licence}", file=sys.stderr)

        sys.exit(1)

    print("✅ LICENCE GATE PASSED - All dependencies use allowed licences")
    logger.info("Licence gate completed successfully")


if __name__ == "__main__":
    main()
