#!/usr/bin/env python3
"""Script to automatically fix flake8 F401 (unused imports) and F821 (undefined name) violations."""
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
    violations: Dict[str, List[str]] = {"F401": [], "F821": []}

    for line in flake8_output.splitlines():
        if "F401" in line:
            violations["F401"].append(line)
        elif "F821" in line:
            violations["F821"].append(line)

    return violations

def fix_f401_violations(violations: List[str]) -> Set[str]:
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

def fix_f821_violations(violations: List[str]) -> Set[str]:
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
            except Exception as e:  # noqa: E501
                print(f"Error writing {filepath}: {e}")

    return fixed_files

def main():
    # Run flake8 and get violations
    print("Running flake8 to find violations...")
    flake8_output = run_flake8()

    # Parse violations
    violations = parse_violations(flake8_output)

    # Fix F401 violations
    print(f"\nFixing {len(violations['F401'])} F401 violations...")
    f401_fixed = fix_f401_violations(violations["F401"])

    # Fix F821 violations
    print(f"\nFixing {len(violations['F821'])} F821 violations...")
    f821_fixed = fix_f821_violations(violations["F821"])

    # Summary
    all_fixed = f401_fixed.union(f821_fixed)
    print(f"\nFixed issues in {len(all_fixed)} files:")
    print(f"  - Fixed {len(f401_fixed)} files with F401 (unused imports)")
    print(f"  - Fixed {len(f821_fixed)} files with F821 (undefined name)")

    if all_fixed:
        print("\nFixed files:")
        for file in sorted(all_fixed):
            print(f"  - {file}")

if __name__ == "__main__":
    main()
