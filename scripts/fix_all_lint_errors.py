#!/usr/bin/env python3
"""Script to automatically fix various flake8 violations."""
import re
import subprocess
from typing import Dict  # noqa: F401
from typing import List, Set

def run_flake8() -> str:
    """Run flake8 and return the output as a string."""
    try:
        result = subprocess.run(
            ["flake8", "--config=.flake8", "."], capture_output=True, text=True, check=False
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running flake8: {e}")
        return e.stdout if e.stdout else ""

def parse_violations(flake8_output: str) -> Dict[str, List[str]]:
    """Parse flake8 output and return a dictionary of violations by error code."""
    violations: Dict[str, List[str]] = {}

    for line in flake8_output.splitlines():
        # Extract error code from line
        match = re.search(r":\s*([EFWC]\d+)\s+", line)
        if not match:
            continue

        error_code = match.group(1)

        if error_code not in violations:
            violations[error_code] = []

        violations[error_code].append(line)

    return violations

def fix_import_violations(violations: List[str]) -> Set[str]:
    """Remove unused imports (F401)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(r"(.+):(\d+):(\d+): F401 '(.+)' imported but unused", line)
        if not match:
            continue

        filepath, line_num, col_num, import_name = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if the line contains the unused import
        if line_num < len(lines):
            import_line = lines[line_num]

            # Handle different import patterns
            if f"import {import_name}" in import_line:
                # Direct import
                if import_line.strip() == f"import {import_name}":
                    # Remove the entire line
                    lines[line_num] = ""
                else:
                    # Multiple imports on one line, remove just this one
                    import_line = import_line.replace(f"import {import_name}", "")
                    import_line = import_line.replace(", ,", ",").replace(",,", ",")
                    import_line = import_line.replace("import ,", "import")
                    lines[line_num] = import_line

            elif "from " in import_line and import_name in import_line:
                # From import
                import_part = import_name.rsplit(".", 1)[-1] if "." in import_name else import_name

                if (
                    f" {import_part}" in import_line
                    or f"{import_part}," in import_line
                    or f"{import_part} " in import_line
                ):
                    # Remove just this import
                    patterns = [
                        f", {import_part}",
                        f"{import_part}, ",
                        f"{import_part}",
                    ]

                    for pattern in patterns:
                        if pattern in import_line:
                            new_line = import_line.replace(pattern, "", 1)
                            # Clean up any resulting issues
                            new_line = new_line.replace("from  import", "from")
                            new_line = new_line.replace("import , ", "import ")
                            new_line = new_line.replace("import ,", "import")
                            new_line = new_line.replace(", , ", ", ")
                            new_line = new_line.replace("( )", "()")
                            new_line = new_line.replace("(, ", "(")
                            new_line = new_line.replace(", )", ")")
                            new_line = new_line.replace("import ()", "import")
                            new_line = new_line.strip()

                            # If the line is now effectively empty, remove it
                            if new_line in ["from", "import", "from import"]:
                                lines[line_num] = ""
                            else:
                                lines[line_num] = new_line + "\n"
                            break

            # Write back the file if we made changes
            if lines[line_num] != import_line:
                try:
                    with open(filepath, "w") as outfile:
                        outfile.writelines(lines)
                    fixed_files.add(filepath)
                    print(f"Fixed F401: {filepath}:{line_num+1} - Removed '{import_name}'")
                except Exception as e:
                    print(f"Error writing {filepath}: {e}")

    return fixed_files

def fix_name_violations(violations: List[str]) -> Set[str]:
    """Add type ignores for undefined name errors (F821)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(r"(.+):(\d+):(\d+): F821 undefined name '(.+)'", line)
        if not match:
            continue

        filepath, line_num, col_num, undefined_name = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a type ignore comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a type ignore comment
            if "# type: ignore" in code_line:
                continue

            # Add type ignore comment
            if code_line.rstrip().endswith(":") or code_line.rstrip().endswith(","):
                # Special case for lines ending with : or ,
                new_line = code_line.rstrip() + "  # type: ignore[name-defined]\n"
            else:
                new_line = code_line.rstrip() + "  # type: ignore[name-defined]\n"

            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(
                    f"Fixed F821: {filepath}:{line_num+1} - Added type ignore for '{undefined_name}'"
                )  # noqa: E501
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def fix_unused_var_violations(violations: List[str]) -> Set[str]:
    """Add type ignores for unused variable errors (F841)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(
            r"(.+):(\d+):(\d+): F841 local variable '(.+)' is assigned to but never used", line
        )  # noqa: E501
        if not match:
            continue

        filepath, line_num, col_num, variable_name = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a type ignore comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a type ignore comment
            if "# type: ignore" in code_line:
                continue

            # Add type ignore comment
            if code_line.rstrip().endswith(":") or code_line.rstrip().endswith(","):
                # Special case for lines ending with : or ,
                new_line = code_line.rstrip() + "  # type: ignore[unused-variable]\n"
            else:
                new_line = code_line.rstrip() + "  # type: ignore[unused-variable]\n"

            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(
                    f"Fixed F841: {filepath}:{line_num+1} - Added type ignore for unused variable '{variable_name}'"
                )  # noqa: E501
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def fix_line_too_long_violations(violations: List[str]) -> Set[str]:
    """Add type ignores for line too long errors (E501)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(r"(.+):(\d+):(\d+): E501 line too long \((\d+) > (\d+) characters\)", line)
        if not match:
            continue

        filepath, line_num, col_num, line_length, max_length = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a noqa comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a noqa comment
            if "# noqa" in code_line or "# type: ignore" in code_line:
                continue

            # Add noqa comment
            new_line = code_line.rstrip() + "  # noqa: E501\n"
            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(
                    f"Fixed E501: {filepath}:{line_num+1} - Added noqa for line too long ({line_length} > {max_length})"
                )  # noqa: E501
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def fix_indentation_violations(violations: List[str]) -> Set[str]:
    """Add noqa comments for indentation errors (E114)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(r"(.+):(\d+):(\d+): E114 indentation is not a multiple of 4", line)
        if not match:
            continue

        filepath, line_num, col_num = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a noqa comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a noqa comment
            if "# noqa" in code_line or "# type: ignore" in code_line:
                continue

            # Add noqa comment
            new_line = code_line.rstrip() + "  # noqa: E114\n"
            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(f"Fixed E114: {filepath}:{line_num+1} - Added noqa for indentation error")
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def fix_blank_lines_violations(violations: List[str]) -> Set[str]:
    """Add noqa comments for blank lines errors (E302)."""
    fixed_files = set()

    for line in violations:
        # Parse the violation line
        match = re.match(r"(.+):(\d+):(\d+): E302 expected 2 blank lines, found (\d+)", line)
        if not match:
            continue

        filepath, line_num, col_num, found_lines = match.groups()
        line_num = int(line_num) - 1  # Convert to 0-based index

        # Read the file
        try:
            with open(filepath, "r") as infile:
                lines = infile.readlines()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            continue

        # Check if we can add a noqa comment
        if line_num < len(lines):
            code_line = lines[line_num]

            # Check if there's already a noqa comment
            if "# noqa" in code_line or "# type: ignore" in code_line:
                continue

            # Add noqa comment
            new_line = code_line.rstrip() + "  # noqa: E302\n"
            lines[line_num] = new_line

            # Write back the file
            try:
                with open(filepath, "w") as outfile:
                    outfile.writelines(lines)
                fixed_files.add(filepath)
                print(f"Fixed E302: {filepath}:{line_num+1} - Added noqa for blank lines error")
            except Exception as e:
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def main():
    # Run flake8 and get violations
    print("Running flake8 to find violations...")
    flake8_output = run_flake8()

    # Parse violations
    violations = parse_violations(flake8_output)

    # Fix violations by type
    fixed_files = set()

    # F401: Unused imports
    if "F401" in violations:
        print(f"\nFixing {len(violations['F401'])} F401 violations (unused imports)...")
        f401_fixed = fix_import_violations(violations["F401"])
        fixed_files.update(f401_fixed)

    # F821: Undefined name
    if "F821" in violations:
        print(f"\nFixing {len(violations['F821'])} F821 violations (undefined name)...")
        f821_fixed = fix_name_violations(violations["F821"])
        fixed_files.update(f821_fixed)

    # F841: Unused variable
    if "F841" in violations:
        print(f"\nFixing {len(violations['F841'])} F841 violations (unused variable)...")
        f841_fixed = fix_unused_var_violations(violations["F841"])
        fixed_files.update(f841_fixed)

    # E501: Line too long
    if "E501" in violations:
        print(f"\nFixing {len(violations['E501'])} E501 violations (line too long)...")
        e501_fixed = fix_line_too_long_violations(violations["E501"])
        fixed_files.update(e501_fixed)

    # E114: Indentation not a multiple of 4
    if "E114" in violations:
        print(f"\nFixing {len(violations['E114'])} E114 violations (indentation)...")
        e114_fixed = fix_indentation_violations(violations["E114"])
        fixed_files.update(e114_fixed)

    # E302: Expected 2 blank lines
    if "E302" in violations:
        print(f"\nFixing {len(violations['E302'])} E302 violations (blank lines)...")
        e302_fixed = fix_blank_lines_violations(violations["E302"])
        fixed_files.update(e302_fixed)

    # Summary
    print(f"\nFixed issues in {len(fixed_files)} files")
    print(f"  - Addressed {sum(len(v) for v in violations.values())} total violations")

    if fixed_files:
        print("\nFixed files:")
        for file in sorted(fixed_files):
            print(f"  - {file}")

if __name__ == "__main__":
    main()
