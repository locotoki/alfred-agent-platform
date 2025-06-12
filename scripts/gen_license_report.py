#!/usr/bin/env python3
"""
License Report Generator - DA-004.

Reads the dependency inventory CSV and uses pip-licenses to gather
license information for each package, with basic classification.

Usage: python scripts/gen_license_report.py
Output: metrics/license_report.csv
"""

import csv
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

# License classification mapping
# SPDX-based license classification mapping
SPDX_LICENSE_CLASSIFICATIONS = {
    # Permissive licenses (SPDX identifiers)
    "MIT": "permissive",
    "BSD-2-Clause": "permissive",
    "BSD-3-Clause": "permissive",
    "Apache-2.0": "permissive",
    "ISC": "permissive",
    "Python-2.0": "permissive",
    "BSD": "permissive",
    "Zlib": "permissive",
    "X11": "permissive",
    "0BSD": "permissive",
    "MS-PL": "permissive",
    # Weak copyleft licenses
    "MPL-2.0": "weak-copyleft",
    "LGPL-2.1": "weak-copyleft",
    "LGPL-3.0": "weak-copyleft",
    "LGPL-2.1-only": "weak-copyleft",
    "LGPL-3.0-only": "weak-copyleft",
    "EPL-1.0": "weak-copyleft",
    "EPL-2.0": "weak-copyleft",
    # Strong copyleft licenses
    "GPL-2.0": "copyleft",
    "GPL-3.0": "copyleft",
    "GPL-2.0-only": "copyleft",
    "GPL-3.0-only": "copyleft",
    "AGPL-3.0": "copyleft",
    "AGPL-3.0-only": "copyleft",
    # Public domain / unlicense
    "Unlicense": "public-domain",
    "CC0-1.0": "public-domain",
    # Proprietary or restrictive
    "BUSL-1.1": "other",
    "Proprietary": "other",
}

# Legacy license name mappings (non-SPDX)
LEGACY_LICENSE_CLASSIFICATIONS = {
    # Permissive licenses (common variations)
    "MIT License": "permissive",
    "Apache Software License": "permissive",
    "Apache License 2.0": "permissive",
    "BSD License": "permissive",
    "3-Clause BSD License": "permissive",
    "2-Clause BSD License": "permissive",
    "ISC License": "permissive",
    "Python Software Foundation License": "permissive",
    "PSF": "permissive",
    # Dual-license combinations (choose most permissive)
    "Apache Software License; BSD License": "permissive",
    "Apache Software License; MIT License": "permissive",
    "BSD License; MIT License": "permissive",
    # Weak copyleft
    "Mozilla Public License 2.0 (MPL 2.0)": "weak-copyleft",
    "Mozilla Public License 2.0": "weak-copyleft",
    "GNU Library or Lesser General Public License (LGPL)": "weak-copyleft",
    "LGPL": "weak-copyleft",
    # Strong copyleft licenses
    "GNU General Public License": "copyleft",
    "GPL": "copyleft",
    "GNU Lesser General Public License": "copyleft",
    "GNU Affero General Public License": "copyleft",
    "AGPL": "copyleft",
    # Public domain / unlicense
    "Public Domain": "public-domain",
    "CC0": "public-domain",
}

def read_dependency_inventory(inventory_path: Path) -> List[Dict[str, str]]:
    """Read the dependency inventory CSV file."""
    packages = []

    if not inventory_path.exists():
        print(f"Warning: Dependency inventory not found at {inventory_path}", file=sys.stderr)
        return packages

    try:
        with open(inventory_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("package"):
                    packages.append(row)
    except Exception as e:
        print(f"Error reading dependency inventory: {e}", file=sys.stderr)

    return packages

def get_package_licenses(packages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Get license information for packages using pip-licenses."""
    license_data = []

    if not packages:
        print("No packages to scan for licenses", file=sys.stderr)
        return license_data

    try:
        # Run pip-licenses with JSON output
        cmd = [sys.executable, "-m", "piplicenses", "--format", "json", "--with-urls"]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            raise RuntimeError(f"pip-licenses failed: {result.stderr}")

        # Parse JSON output

        import json
        try:
            licenses_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Failed to parse pip-licenses JSON output", file=sys.stderr)
            return license_data

        # Create a mapping of package names to license info
        license_map = {}
        for item in licenses_info:
            pkg_name = item.get("Name", "").lower()
            license_name = item.get("License", "unknown")
            version = item.get("Version", "unknown")

            license_map[pkg_name] = {"license": license_name, "version": version}

        # Match packages from inventory with license information
        for pkg in packages:
            pkg_name = pkg["package"].lower()

            if pkg_name in license_map:
                license_info = license_map[pkg_name]
                license_name = license_info["license"]
                classification = classify_license(license_name)

                license_data.append(
                    {
                        "package": pkg["package"],
                        "version": license_info["version"],
                        "license": license_name,
                        "license_classification": classification,
                    }
                )
            else:
                # Package not found in pip-licenses output
                license_data.append(
                    {
                        "package": pkg["package"],
                        "version": pkg.get("declared_version", "unknown"),
                        "license": "not-found",
                        "license_classification": "unknown",
                    }
                )

    except subprocess.TimeoutExpired:
        raise RuntimeError("pip-licenses timed out after 2 minutes")
    except FileNotFoundError:
        raise RuntimeError("pip-licenses not found. Install with: pip install pip-licenses")
    except Exception as e:
        raise RuntimeError(f"Error running pip-licenses: {e}")

    return license_data

def classify_license(license_name: str) -> str:
    """Classify a license into a category."""
    if not license_name or license_name.lower() in ["unknown", "not-found"]:
        return "unknown"

    # Try SPDX identifiers first (more precise)
    classification = SPDX_LICENSE_CLASSIFICATIONS.get(license_name)
    if classification:
        return classification

    # Try legacy license name mappings
    classification = LEGACY_LICENSE_CLASSIFICATIONS.get(license_name)
    if classification:
        return classification

    # No fuzzy matching - require exact SPDX or legacy mapping
    return "other"

def write_license_report(license_data: List[Dict[str, str]], output_path: Path):
    """Write the license report to CSV."""
    # Ensure output directory exists
    output_path.parent.mkdir(exist_ok=True)

    fieldnames = ["package", "version", "license", "license_classification"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(license_data)

    print(f"License report written with {len(license_data)} entries: {output_path}")

def main():
    """Generate license report from dependency inventory."""
    repo_root = Path(__file__).parent.parent
    inventory_path = repo_root / "metrics" / "dependency_inventory.csv"
    output_path = repo_root / "metrics" / "license_report.csv"

    print(f"Reading dependency inventory from {inventory_path}")
    packages = read_dependency_inventory(inventory_path)

    print(f"Gathering license information for {len(packages)} packages")
    license_data = get_package_licenses(packages)

    write_license_report(license_data, output_path)

    # Print summary statistics
    if license_data:
        classifications = {}
        for item in license_data:
            classification = item["license_classification"]
            classifications[classification] = classifications.get(classification, 0) + 1

        print("\nLicense classification summary:")
        for classification, count in sorted(classifications.items()):
            print(f"  {classification}: {count}")

    # Assert unknown/other ratio is acceptable
    if license_data:
        unknown_count = sum(
            1 for item in license_data if item["license_classification"] in ["unknown", "other"]
        )
        total_count = len(license_data)
        unknown_ratio = unknown_count / total_count

        if unknown_ratio > 0.10:
            raise AssertionError(
                f"Unknown/other license ratio too high: {unknown_ratio:.1%} ({unknown_count}/{total_count}). "
                "Expected ≤10%. Check SPDX mappings in script or filter dependency inventory."
            )

        print(f"Unknown/other ratio: {unknown_ratio:.1%} ({unknown_count}/{total_count}) - OK")

    print("License report generation completed")

if __name__ == "__main__":
    main()
