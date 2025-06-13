#!/usr/bin/env python3
"""
Dependency Inventory Generator - DA-001.

Walks the repository to parse all requirements*.txt and pyproject.toml files,
analyzes import graphs via modulegraph, and emits a CSV inventory.

Usage: python scripts/gen_dependency_inventory.py
Output: metrics/dependency_inventory.csv
"""

import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    import tomllib
except ImportError:
    import tomli as tomllib
try:
    from modulegraph import modulegraph
except ImportError:
    modulegraph = None

def find_dependency_files(repo_root: Path) -> List[Path]:
    """Find all requirements*.txt and pyproject.toml files in the repo."""
    files = []

    # Find requirements*.txt files
    for req_file in repo_root.rglob("requirements*.txt"):
        if "backup" not in str(req_file) and "cleanup-temp" not in str(req_file):
            files.append(req_file)

    # Find pyproject.toml files
    for toml_file in repo_root.rglob("pyproject.toml"):
        if "backup" not in str(toml_file) and "cleanup-temp" not in str(toml_file):
            files.append(toml_file)

    return sorted(files)

def parse_requirements_txt(file_path: Path) -> List[Tuple[str, str]]:
    """Parse requirements.txt file and extract package names with versions."""
    packages = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines, comments, and git/url dependencies
                if (
                    not line
                    or line.startswith("#")
                    or line.startswith("git+")
                    or line.startswith("http")
                ):
                    continue

                # Handle -r includes
                if line.startswith("-r "):
                    continue

                # Parse package specification
                # Remove options like --index-url, --trusted-host
                if line.startswith("-"):
                    continue

                # Extract package name and version
                package_spec = re.split(r"[><=!;]", line)[0].strip()
                if package_spec:
                    # Extract version constraint
                    version_match = re.search(r"([><=!]+\s*[\d\w\.\-\+]+)", line)
                    version = version_match.group(1) if version_match else ""
                    packages.append((package_spec, version))

    except Exception as e:
        print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)

    return packages

def parse_pyproject_toml(file_path: Path) -> List[Tuple[str, str]]:
    """Parse pyproject.toml file and extract dependencies."""
    packages = []

    try:
        with open(file_path, "rb") as f:
            data = tomllib.load(f)

        # Look for dependencies in various sections
        dep_sections = [
            data.get("project", {}).get("dependencies", []),
            data.get("tool", {}).get("poetry", {}).get("dependencies", {}),
            data.get("build-system", {}).get("requires", []),
        ]

        for deps in dep_sections:
            if isinstance(deps, list):
                # project.dependencies format
                for dep in deps:
                    if isinstance(dep, str):
                        package_spec = re.split(r"[><=!;]", dep)[0].strip()
                        version_match = re.search(r"([><=!]+\s*[\d\w\.\-\+]+)", dep)
                        version = version_match.group(1) if version_match else ""
                        packages.append((package_spec, version))
            elif isinstance(deps, dict):
                # poetry dependencies format
                for pkg_name, pkg_spec in deps.items():
                    if pkg_name == "python":
                        continue
                    if isinstance(pkg_spec, str):
                        packages.append((pkg_name, pkg_spec))
                    elif isinstance(pkg_spec, dict):
                        version = pkg_spec.get("version", "")
                        packages.append((pkg_name, version))

    except Exception as e:
        print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)

    return packages

def analyze_imports(repo_root: Path) -> Set[str]:
    """Analyze Python files to discover imported packages."""
    imports = set()

    # Find all Python files
    for py_file in repo_root.rglob("*.py"):
        if any(
            skip in str(py_file)
            for skip in [
                "backup",
                "cleanup-temp",
                ".venv",
                ".env",
                "venv",
                "env",
                "node_modules",
                ".git",
            ]
        ):
            continue

        try:
            with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Extract import statements
            import_lines = re.findall(
                r"^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)", content, re.MULTILINE
            )
            for imp in import_lines:
                # Get the top-level package
                top_level = imp.split(".")[0]
                if top_level not in {
                    "alfred",
                    "services",
                    "api",
                    "tests",
                } and not top_level.startswith("_"):
                    imports.add(top_level)

        except Exception as e:
            print(f"Warning: Failed to analyze {py_file}: {e}", file=sys.stderr)

    return imports

def get_latest_version(package_name: str) -> str:
    """Get the latest version of a package from PyPI."""
    # For now, return empty to avoid network calls and timeouts
    # This can be enhanced later with batch PyPI API calls
    return ""

def generate_inventory(repo_root: Path) -> List[Dict[str, str]]:
    """Generate the complete dependency inventory."""
    inventory = []
    seen_packages = {}

    # Find and parse dependency files
    dep_files = find_dependency_files(repo_root)

    for file_path in dep_files:
        if file_path.suffix == ".txt":
            packages = parse_requirements_txt(file_path)
        else:
            packages = parse_pyproject_toml(file_path)

        for package, version in packages:
            if package not in seen_packages:
                seen_packages[package] = []
            seen_packages[package].append(
                {"version": version, "location": str(file_path.relative_to(repo_root))}
            )

    # Analyze imports to find additional packages
    imported_packages = analyze_imports(repo_root)

    # Build final inventory
    for package in sorted(set(seen_packages.keys()) | imported_packages):
        if package in seen_packages:
            # Package declared in dependency files
            for entry in seen_packages[package]:
                inventory.append(
                    {
                        "package": package,
                        "declared_version": entry["version"],
                        "latest_pinned": get_latest_version(package),
                        "location": entry["location"],
                    }
                )
        else:
            # Package only found in imports
            inventory.append(
                {
                    "package": package,
                    "declared_version": "",
                    "latest_pinned": get_latest_version(package),
                    "location": "import-only",
                }
            )

    return inventory

def main():
    """Generate dependency inventory CSV file."""
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "metrics" / "dependency_inventory.csv"

    print(f"Generating dependency inventory for {repo_root}")

    # Ensure output directory exists
    output_path.parent.mkdir(exist_ok=True)

    # Generate inventory
    inventory = generate_inventory(repo_root)

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["package", "declared_version", "latest_pinned", "location"]
        )
        writer.writeheader()
        writer.writerows(inventory)

    print(f"Generated inventory with {len(inventory)} entries: {output_path}")

if __name__ == "__main__":
    main()
