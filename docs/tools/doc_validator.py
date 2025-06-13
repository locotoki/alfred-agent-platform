#!/usr/bin/env python3
"""Documentation Validator Script.

This tool validates Markdown documentation files against the Alfred Agent Platform
documentation standards. It checks for compliance with formatting, metadata requirements,
link validity, heading hierarchy, code block specifications, and duplicate content.

Usage:
    python doc_validator.py [options] <path_to_docs>

Options:
    --single-file FILE      Validate a single file
    --report FILE           Output report to file (default: validation_report.md)
    --fix                   Generate fixes for common issues
    --fix-metadata          Automatically add missing metadata to documents
    --owner OWNER           Specify the owner for metadata fixes (default: "Documentation Team")
    --verbose               Show detailed output
    --check-links           Perform link validation (may be time-consuming)
    --dry-run               Show changes that would be made without actually making them
    --batch                 Run in batch mode on an entire directory
    --help                  Show this help message

Examples:
    # Validate all docs in the docs directory
    python doc_validator.py /path/to/docs

    # Validate a single file
    python doc_validator.py --single-file /path/to/docs/file.md

    # Generate a validation report with fix suggestions
    python doc_validator.py --report report.md --fix /path/to/docs

    # Automatically add missing metadata
    python doc_validator.py --fix-metadata --single-file /path/to/docs/file.md

    # Batch fix metadata for all files in a directory
    python doc_validator.py --fix-metadata --batch /path/to/docs

    # Show metadata changes without making them
    python doc_validator.py --fix-metadata --dry-run /path/to/docs

"""

import argparse
import logging
import os
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("doc_validator")

# Documentation standards constants
REQUIRED_METADATA = ["Last Updated", "Owner", "Status"]
DATE_FORMAT = r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
INTERNAL_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
METADATA_PATTERN = re.compile(r"\*\*([^:]+):\*\*\s*(.*?)(?:\s{2,}|\n)", re.MULTILINE)
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

@dataclass
class ValidationIssue:
    """Represents a validation issue found in a document."""

    file: str
    line_number: int
    issue_type: str
    description: str
    suggestion: Optional[str] = None
    severity: str = "warning"  # "error", "warning", or "info"

@dataclass
class ValidationResult:
    """Collects validation results for a document."""

    file_path: str
    issues: List[ValidationIssue]
    is_valid: bool
    metadata: Dict[str, str]
    statistics: Dict[str, Any]

class DocumentValidator:
    """Validates Markdown documentation files against the Alfred Agent Platform
    standards.
    """

    def __init__(self, base_path: str, check_links: bool = False, verbose: bool = False):
        """Initialize the validator.

        Args:
            base_path: Base path of the documentation directory
            check_links: Whether to check link validity
            verbose: Whether to show detailed output

        """
        self.base_path = Path(base_path)
        self.check_links = check_links
        self.verbose = verbose
        self.results: List[ValidationResult] = []
        self.heading_counts = defaultdict(int)

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate a single Markdown file.

        Args:
            file_path: Path to the Markdown file to validate

        Returns:
            ValidationResult containing issues found and statistics

        """
        path = Path(file_path)
        if not path.exists():
            return ValidationResult(
                file_path=file_path,
                issues=[
                    ValidationIssue(
                        file=file_path,
                        line_number=0,
                        issue_type="file_missing",
                        description=f"File does not exist: {file_path}",
                        severity="error",
                    )
                ],
                is_valid=False,
                metadata={},
                statistics={},
            )

        if path.suffix.lower() != ".md":
            return ValidationResult(
                file_path=file_path,
                issues=[
                    ValidationIssue(
                        file=file_path,
                        line_number=0,
                        issue_type="invalid_file_type",
                        description=f"Not a Markdown file: {file_path}",
                        severity="error",
                    )
                ],
                is_valid=False,
                metadata={},
                statistics={},
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")
        except Exception as e:
            return ValidationResult(
                file_path=file_path,
                issues=[
                    ValidationIssue(
                        file=file_path,
                        line_number=0,
                        issue_type="file_read_error",
                        description=f"Could not read file: {e}",
                        severity="error",
                    )
                ],
                is_valid=False,
                metadata={},
                statistics={},
            )

        issues: List[ValidationIssue] = []
        issues.extend(self._validate_metadata(file_path, content, lines))
        issues.extend(self._validate_heading_hierarchy(file_path, content, lines))
        issues.extend(self._validate_code_blocks(file_path, content, lines))

        if self.check_links:
            issues.extend(self._validate_links(file_path, content, lines))

        # Calculate statistics
        statistics = {
            "total_lines": len(lines),
            "headings": len(HEADING_PATTERN.findall(content)),
            "code_blocks": len(CODE_BLOCK_PATTERN.findall(content)),
            "internal_links": len(INTERNAL_LINK_PATTERN.findall(content)),
        }

        # Extract metadata
        metadata = self._extract_metadata(content)

        is_valid = all(issue.severity != "error" for issue in issues)

        result = ValidationResult(
            file_path=file_path,
            issues=issues,
            is_valid=is_valid,
            metadata=metadata,
            statistics=statistics,
        )

        self.results.append(result)
        return result

    def validate_all(self) -> List[ValidationResult]:
        """Validate all Markdown files in the specified directory.

        Returns:
            List of ValidationResults for all files.

        """
        md_files = list(self.base_path.glob("**/*.md"))
        logger.info(f"Found {len(md_files)} Markdown files to validate")

        for file_path in md_files:
            relative_path = file_path.relative_to(self.base_path)
            if self.verbose:
                logger.info(f"Validating {relative_path}")
            result = self.validate_file(str(file_path))
            if not result.is_valid and self.verbose:
                logger.warning(f"Validation failed for {relative_path}")

        self._check_duplicate_content()
        return self.results

    def _extract_metadata(self, content: str) -> Dict[str, str]:
        """Extract metadata from document content."""
        metadata = {}

        # Extract title
        title_match = TITLE_PATTERN.search(content)
        if title_match:
            metadata["Title"] = title_match.group(1).strip()

        # Extract other metadata
        metadata_matches = METADATA_PATTERN.finditer(content)
        for match in metadata_matches:
            key = match.group(1).strip()
            value = match.group(2).strip()
            metadata[key] = value

        return metadata

    def _validate_metadata(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[ValidationIssue]:
        """Validate document metadata requirements."""
        issues = []
        metadata = self._extract_metadata(content)

        # Check for title (# Document Title)
        if "Title" not in metadata:
            issues.append(
                ValidationIssue(
                    file=file_path,
                    line_number=1,
                    issue_type="missing_title",
                    description="Document title is missing. Add a level 1 heading at the beginning.",
                    suggestion="# Document Title",
                    severity="error",
                )
            )

        # Check for required metadata fields
        for field in REQUIRED_METADATA:
            if field not in metadata:
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=3,  # Approximate location after title
                        issue_type="missing_metadata",
                        description=f"Required metadata field missing: {field}",
                        suggestion=f"**{field}:** [value]",
                        severity="error",
                    )
                )

        # Validate date format if present
        if "Last Updated" in metadata:
            date_str = metadata["Last Updated"]
            if not re.match(DATE_FORMAT, date_str):
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=0,  # We don't know the exact line number
                        issue_type="invalid_date_format",
                        description=f"Invalid date format: {date_str}. Use YYYY-MM-DD format.",
                        suggestion=f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}",
                        severity="error",
                    )
                )

        return issues

    def _validate_heading_hierarchy(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[ValidationIssue]:
        """Validate heading hierarchy (no skipped levels)."""
        issues = []
        heading_matches = HEADING_PATTERN.finditer(content)
        current_level = 0
        previous_headings = defaultdict(str)

        for match in heading_matches:
            heading_marker = match.group(1)
            heading_text = match.group(2).strip()
            level = len(heading_marker)

            # Find line number
            line_number = content[: match.start()].count("\n") + 1

            # Track heading counts for duplicate detection
            self.heading_counts[heading_text.lower()] += 1

            # Check for skipped levels
            if level > current_level + 1 and current_level > 0:
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=line_number,
                        issue_type="skipped_heading_level",
                        description=f"Skipped heading level: {heading_marker} {heading_text} (jumped from h{current_level} to h{level})",
                        suggestion=f"{'#' * (current_level + 1)} {heading_text}",
                        severity="error",
                    )
                )

            # Check for capitalization (sentence case)
            if not heading_text[0].isupper():
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=line_number,
                        issue_type="heading_capitalization",
                        description=f"Heading should use sentence case (first word capitalized): {heading_text}",
                        suggestion=f"{heading_marker} {heading_text[0].upper()}{heading_text[1:]}",
                        severity="warning",
                    )
                )

            # Store for later duplicate checks
            previous_headings[level] = heading_text
            current_level = level

        return issues

    def _validate_code_blocks(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[ValidationIssue]:
        """Validate code blocks (language specification)."""
        issues = []
        code_block_matches = CODE_BLOCK_PATTERN.finditer(content)

        for match in code_block_matches:
            language = match.group(1)
            match.group(2)

            # Find line number
            line_number = content[: match.start()].count("\n") + 1

            if not language:
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=line_number,
                        issue_type="missing_language_spec",
                        description="Code block is missing language specification",
                        suggestion="Add a language identifier after the opening ```",
                        severity="warning",
                    )
                )

        return issues

    def _validate_links(
        self, file_path: str, content: str, lines: List[str]
    ) -> List[ValidationIssue]:
        """Validate internal links."""
        issues = []
        base_dir = Path(file_path).parent
        link_matches = INTERNAL_LINK_PATTERN.finditer(content)

        for match in link_matches:
            match.group(1)
            link_target = match.group(2)

            # Find line number
            line_number = content[: match.start()].count("\n") + 1

            # Only check relative internal links
            if link_target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # Validate internal link
            target_path = base_dir / link_target
            if not target_path.exists() and not link_target.startswith("#"):
                issues.append(
                    ValidationIssue(
                        file=file_path,
                        line_number=line_number,
                        issue_type="broken_internal_link",
                        description=f"Broken internal link: {link_target}",
                        suggestion="Update with correct relative path",
                        severity="error",
                    )
                )

        return issues

    def _check_duplicate_content(self) -> None:
        """Check for potential duplicate content across files.

        This method is called after all files have been validated.
        """
        # Find headings that appear multiple times
        potential_duplicates = {
            heading: count for heading, count in self.heading_counts.items() if count > 1
        }

        if not potential_duplicates:
            return

        # For files with duplicate headings, add a warning
        for result in self.results:
            with open(result.file_path, "r", encoding="utf-8") as f:
                content = f.read().lower()

            for heading, count in potential_duplicates.items():
                if heading in content:
                    # This is a simple heuristic; more sophisticated duplicate detection
                    # would involve comparing actual content under these headings
                    result.issues.append(
                        ValidationIssue(
                            file=result.file_path,
                            line_number=0,  # We don't know the exact line
                            issue_type="potential_duplicate_content",
                            description=f"Potential duplicate content: '{heading}' appears in {count} documents",
                            suggestion="Consider consolidating or refactoring duplicate content",
                            severity="info",
                        )
                    )

    def generate_report(
        self, output_file: str = "validation_report.md", suggest_fixes: bool = False
    ) -> str:
        """Generate a Markdown report of validation results.

        Args:
            output_file: Path to write the report to
            suggest_fixes: Whether to include suggested fixes

        Returns:
            Path to the generated report file.

        """
        error_count = sum(
            1 for result in self.results for issue in result.issues if issue.severity == "error"
        )
        warning_count = sum(
            1 for result in self.results for issue in result.issues if issue.severity == "warning"
        )
        info_count = sum(
            1 for result in self.results for issue in result.issues if issue.severity == "info"
        )

        valid_count = sum(1 for result in self.results if result.is_valid)
        total_count = len(self.results)

        if total_count == 0:
            logger.warning("No files were validated. Check your path.")
            return "No files were validated"

        compliance_rate = (valid_count / total_count) * 100

        report = [
            "# Documentation Standards Validation Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Base Path:** {self.base_path}",
            "",
            "## Summary",
            "",
            f"- **Files Analyzed:** {total_count}",
            f"- **Compliant Files:** {valid_count} ({compliance_rate:.1f}%)",
            f"- **Issues Found:** {error_count + warning_count + info_count}",
            f"  - Errors: {error_count}",
            f"  - Warnings: {warning_count}",
            f"  - Info: {info_count}",
            "",
        ]

        # Sort results by validity and number of issues
        sorted_results = sorted(
            self.results,
            key=lambda r: (
                r.is_valid,
                len([i for i in r.issues if i.severity == "error"]),
            ),
        )

        # Add issues section
        report.append("## Issues by File")
        report.append("")

        for result in sorted_results:
            if not result.issues:
                continue

            relative_path = Path(result.file_path).relative_to(self.base_path)
            report.append(f"### {relative_path}")
            report.append("")

            if result.is_valid:
                report.append("✅ **Compliant with minor issues**")
            else:
                report.append("❌ **Non-compliant**")
            report.append("")

            # Sort issues by severity and line number
            sorted_issues = sorted(
                result.issues,
                key=lambda i: (
                    (0 if i.severity == "error" else (1 if i.severity == "warning" else 2)),
                    i.line_number,
                ),
            )

            if sorted_issues:
                report.append("| Line | Type | Severity | Description |")
                report.append("|------|------|----------|-------------|")

                for issue in sorted_issues:
                    severity_indicator = (
                        "🔴"
                        if issue.severity == "error"
                        else ("🟠" if issue.severity == "warning" else "🔵")
                    )
                    line_info = str(issue.line_number) if issue.line_number > 0 else "-"
                    report.append(
                        f"| {line_info} | {issue.issue_type} | {severity_indicator} {issue.severity} | {issue.description} |"
                    )

                report.append("")

            # Add suggestions section if requested
            if suggest_fixes and any(issue.suggestion for issue in result.issues):
                report.append("#### Suggested Fixes")
                report.append("")

                for issue in [i for i in sorted_issues if i.suggestion]:
                    report.append(f"- **Line {issue.line_number}** ({issue.issue_type}):")
                    report.append("  ```")
                    report.append(f"  {issue.suggestion}")
                    report.append("  ```")

                report.append("")

        # Add compliant files section
        compliant_files = [
            result for result in self.results if result.is_valid and not result.issues
        ]
        if compliant_files:
            report.append("## Fully Compliant Files")
            report.append("")
            report.append(
                "The following files are fully compliant with all documentation standards:"
            )
            report.append("")

            for result in compliant_files:
                relative_path = Path(result.file_path).relative_to(self.base_path)
                report.append(f"- ✅ {relative_path}")

            report.append("")

        # Write report to file
        report_path = os.path.join(os.getcwd(), output_file)
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report))
            logger.info(f"Report generated: {report_path}")
        except Exception as e:
            logger.error(f"Failed to write report: {e}")
            return str(e)

        return report_path

def main():
    parser = argparse.ArgumentParser(
        description="Validate documentation against Alfred Agent Platform standards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("path", nargs="?", default=None, help="Path to documentation directory")
    parser.add_argument("--single-file", help="Validate a single file")
    parser.add_argument("--report", default="validation_report.md", help="Output report to file")
    parser.add_argument("--fix", action="store_true", help="Generate fixes for common issues")
    parser.add_argument(
        "--fix-metadata",
        action="store_true",
        help="Automatically add missing metadata to documents",
    )
    parser.add_argument(
        "--owner",
        default="Documentation Team",
        help="Specify the owner for metadata fixes",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--check-links", action="store_true", help="Perform link validation")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without making them")
    parser.add_argument(
        "--batch", action="store_true", help="Run in batch mode on an entire directory"
    )

    args = parser.parse_args()

    # Determine path to validate
    validate_path = args.path

    if args.single_file:
        validate_path = os.path.dirname(args.single_file)
        if not validate_path:
            validate_path = "."

    if not validate_path:
        parser.print_help()
        sys.exit(1)

    # Initialize and run validator
    validator = DocumentValidator(
        base_path=validate_path, check_links=args.check_links, verbose=args.verbose
    )

    # Fix metadata if requested
    if args.fix_metadata:
        metadata_fixer = MetadataFixer(owner=args.owner, dry_run=args.dry_run, verbose=args.verbose)

        if args.single_file:
            metadata_fixer.fix_single_file(args.single_file)
        elif args.batch:
            metadata_fixer.fix_directory(validate_path)
        else:
            logger.info("Processing all Markdown files in the specified directory...")
            metadata_fixer.fix_directory(validate_path)
    # Validate files
    elif args.single_file:
        result = validator.validate_file(args.single_file)
        if not result.is_valid:
            logger.error(f"Validation failed for {args.single_file}")
            for issue in result.issues:
                logger.error(f"{issue.severity.upper()}: {issue.description}")
    else:
        validator.validate_all()

        # Generate report
        report_path = validator.generate_report(args.report, args.fix)
        print(f"Validation complete. Report saved to: {report_path}")

        # Return error code if any errors found
        if any(not result.is_valid for result in validator.results):
            sys.exit(1)

class MetadataFixer:
    """A class to automatically add or fix metadata in Markdown documentation
    files.
    """

    def __init__(
        self,
        owner: str = "Documentation Team",
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """Initialize the metadata fixer.

        Args:
            owner: Default owner to use for metadata
            dry_run: If True, show changes without making them
            verbose: Show detailed output.

        """
        self.owner = owner
        self.dry_run = dry_run
        self.verbose = verbose
        self.fixed_files = []
        self.today = datetime.now().strftime("%Y-%m-%d")

        # Alternative metadata patterns that might be present in different formats
        self.alt_metadata_patterns = [
            re.compile(r"^(\w+):\s*(.*?)$", re.MULTILINE),  # Simple key: value format
            re.compile(r"^<!--\s*(\w+):\s*(.*?)\s*-->$", re.MULTILINE),  # HTML comment format
            re.compile(r"^---\s*$(.+?)^---\s*$", re.DOTALL | re.MULTILINE),  # YAML frontmatter
        ]

    def extract_yaml_frontmatter(self, content: str) -> Dict[str, str]:
        """Extract metadata from YAML frontmatter."""
        frontmatter_match = re.search(r"^---\s*$(.+?)^---\s*$", content, re.DOTALL | re.MULTILINE)
        if not frontmatter_match:
            return {}

        metadata = {}
        frontmatter = frontmatter_match.group(1)

        # Simple parsing of YAML frontmatter
        for line in frontmatter.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        return metadata

    def detect_metadata_format(self, content: str) -> Tuple[str, Dict[str, str]]:
        """Detect what format the metadata is in, if any.

        Returns:
            Tuple of (format_type, metadata_dict)
            format_type can be "standard", "yaml", "simple", "comment", or "none"

        """
        # Check for standard format first
        standard_metadata = METADATA_PATTERN.finditer(content)
        metadata_dict = {}

        for match in standard_metadata:
            key = match.group(1).strip()
            value = match.group(2).strip()
            metadata_dict[key] = value

        if metadata_dict:
            return "standard", metadata_dict

        # Check for YAML frontmatter
        yaml_metadata = self.extract_yaml_frontmatter(content)
        if yaml_metadata:
            return "yaml", yaml_metadata

        # Check for simple key: value format
        simple_format = self.alt_metadata_patterns[0].finditer(content.split("\n\n")[0])
        simple_metadata = {}

        for match in simple_format:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key in REQUIRED_METADATA or key in ["Title", "Author"]:
                simple_metadata[key] = value

        if simple_metadata:
            return "simple", simple_metadata

        # Check for HTML comment format
        comment_format = self.alt_metadata_patterns[1].finditer(content)
        comment_metadata = {}

        for match in comment_format:
            key = match.group(1).strip()
            value = match.group(2).strip()
            comment_metadata[key] = value

        if comment_metadata:
            return "comment", comment_metadata

        return "none", {}

    def generate_metadata_block(
        self, title: Optional[str], existing_metadata: Dict[str, str]
    ) -> str:
        """Generate a metadata block with the specified title and any existing
        metadata.

        Args:
            title: Document title (extracted from heading)
            existing_metadata: Any existing metadata to include

        Returns:
            Formatted metadata block as string.

        """
        metadata_lines = []

        # Add all existing metadata
        for field in REQUIRED_METADATA:
            if field == "Last Updated":
                metadata_lines.append(f"**{field}:** {self.today}")
            elif field == "Owner" and field not in existing_metadata:
                metadata_lines.append(f"**{field}:** {self.owner}")
            elif field == "Status" and field not in existing_metadata:
                metadata_lines.append(f"**{field}:** Draft")
            elif field in existing_metadata:
                metadata_lines.append(f"**{field}:** {existing_metadata[field]}")
            else:
                metadata_lines.append(f"**{field}:** ")

        # Add any other existing metadata not in required fields
        for key, value in existing_metadata.items():
            if key not in REQUIRED_METADATA and key != "Title":
                metadata_lines.append(f"**{key}:** {value}")

        return "\n".join(metadata_lines)

    def fix_metadata(self, file_path: str) -> bool:
        """Add or fix metadata in a Markdown file.

        Args:
            file_path: Path to the file to fix

        Returns:
            True if changes were made, False otherwise.

        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return False

        # Create backup of the file
        if not self.dry_run:
            backup_path = f"{file_path}.bak"
            try:
                shutil.copy2(file_path, backup_path)
                if self.verbose:
                    logger.info(f"Created backup at {backup_path}")
            except Exception as e:
                logger.error(f"Failed to create backup of {file_path}: {e}")
                return False

        # Extract title from content
        title_match = TITLE_PATTERN.search(content)
        title = title_match.group(1).strip() if title_match else None

        # Detect existing metadata format
        format_type, existing_metadata = self.detect_metadata_format(content)

        if self.verbose:
            logger.info(f"Detected metadata format: {format_type}")
            if existing_metadata:
                logger.info(f"Existing metadata: {existing_metadata}")

        # Generate new metadata block
        new_metadata_block = self.generate_metadata_block(title, existing_metadata)

        # Determine where to insert the metadata and how to modify the file
        if format_type == "standard":
            # Metadata already exists in the standard format - update it
            if self.verbose:
                logger.info("Updating existing standard format metadata")

            # Find the metadata block
            metadata_start = None
            metadata_end = None
            lines = content.split("\n")
            in_metadata = False

            for i, line in enumerate(lines):
                if re.match(r"\*\*[^:]+:\*\*", line) and not in_metadata:
                    metadata_start = i
                    in_metadata = True
                elif in_metadata and not re.match(r"\*\*[^:]+:\*\*", line) and line.strip():
                    metadata_end = i
                    break

            if metadata_end is None and in_metadata:
                metadata_end = len(lines)

            if metadata_start is not None and metadata_end is not None:
                # Replace the metadata block
                new_lines = (
                    lines[:metadata_start] + new_metadata_block.split("\n") + lines[metadata_end:]
                )
                new_content = "\n".join(new_lines)
            else:
                # Couldn't find the block bounds - don't modify
                logger.warning(f"Could not locate metadata block bounds in {file_path}")
                return False

        elif format_type in ["yaml", "simple", "comment"]:
            # Convert from a different format to standard format
            if self.verbose:
                logger.info(f"Converting from {format_type} format to standard format")

            if format_type == "yaml":
                # Remove YAML frontmatter
                new_content = re.sub(
                    r"^---\s*$(.+?)^---\s*$",
                    "",
                    content,
                    flags=re.DOTALL | re.MULTILINE,
                )
            elif format_type == "simple":
                # Remove simple format metadata from the top
                lines = content.split("\n")
                skip_to = 0
                for i, line in enumerate(lines):
                    if re.match(r"^\w+:\s*.*?$", line):
                        skip_to = i + 1
                    elif line.strip() and not line.startswith("#"):
                        break
                new_content = "\n".join(lines[skip_to:])
            else:  # comment format
                # Remove HTML comment metadata
                new_content = re.sub(r"^<!--\s*\w+:\s*.*?\s*-->$", "", content, flags=re.MULTILINE)

            # Insert title and metadata after the title
            if title_match:
                title_end = title_match.end()
                new_content = (
                    content[:title_end]
                    + "\n\n"
                    + new_metadata_block
                    + "\n\n"
                    + content[title_end:].lstrip()
                )
            else:
                # No title found, add metadata at the top
                new_content = new_metadata_block + "\n\n" + content
        else:
            # No metadata found - add new metadata
            if self.verbose:
                logger.info("No metadata found, adding new metadata block")

            if title_match:
                # Insert metadata after the title
                title_end = title_match.end()
                new_content = (
                    content[:title_end]
                    + "\n\n"
                    + new_metadata_block
                    + "\n\n"
                    + content[title_end:].lstrip()
                )
            else:
                # No title found, add metadata at the top
                new_content = new_metadata_block + "\n\n" + content

        # If this is a dry run, just show the changes
        if self.dry_run:
            logger.info(f"DRY RUN: Would update metadata in {file_path}")
            return True

        # Write the changes
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"Updated metadata in {file_path}")
            self.fixed_files.append(file_path)
            return True
        except Exception as e:
            logger.error(f"Error writing to {file_path}: {e}")
            # Restore backup
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(f"Restored backup of {file_path}")
            except Exception as e2:
                logger.error(f"Failed to restore backup of {file_path}: {e2}")
            return False

    def fix_single_file(self, file_path: str) -> bool:
        """Fix metadata in a single file."""
        if not os.path.exists(file_path):
            logger.error(f"File does not exist: {file_path}")
            return False

        if not file_path.lower().endswith(".md"):
            logger.error(f"Not a Markdown file: {file_path}")
            return False

        logger.info(f"Processing file: {file_path}")
        return self.fix_metadata(file_path)

    def fix_directory(self, dir_path: str) -> List[str]:
        """Fix metadata in all Markdown files in a directory.

        Args:
            dir_path: Path to the directory

        Returns:
            List of fixed file paths.

        """
        self.fixed_files = []

        if not os.path.isdir(dir_path):
            logger.error(f"Not a directory: {dir_path}")
            return []

        # Find all Markdown files
        md_files = list(Path(dir_path).glob("**/*.md"))
        logger.info(f"Found {len(md_files)} Markdown files to process")

        for file_path in md_files:
            try:
                if self.verbose:
                    logger.info(f"Processing {file_path}")
                self.fix_metadata(str(file_path))
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

        # Generate report
        self.generate_report()

        return self.fixed_files

    def generate_report(self) -> None:
        """Generate a report of fixed files."""
        if not self.fixed_files:
            if self.dry_run:
                logger.info("DRY RUN: No files would be modified")
            else:
                logger.info("No files were modified")
            return

        if self.dry_run:
            logger.info(f"DRY RUN: Would modify {len(self.fixed_files)} files:")
        else:
            logger.info(f"Modified {len(self.fixed_files)} files:")

        for file_path in self.fixed_files:
            logger.info(f"  - {file_path}")

if __name__ == "__main__":
    main()
