#!/usr/bin/env python3
"""Documentation Metadata Updater.

This tool automates the addition and standardization of metadata in Markdown documentation files.
It can process individual files or entire directories, adding missing metadata or standardizing
existing metadata according to the Alfred Agent Platform documentation standards.

Usage:
    python update_metadata.py [options] <path>

Options:
    --owner NAME          Set the document owner (default: "Documentation Team")
    --status STATUS       Set the document status (default: "Draft")
    --force               Overwrite existing metadata
    --dry-run             Show what would be changed without modifying files
    --batch               Process all markdown files in directory and subdirectories
    --report FILE         Save report to specified file
    --quiet               Suppress console output
"""

import argparse
import datetime
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

class MetadataUpdater:
    """Class to update metadata in markdown files."""

    # Metadata fields and their regex patterns
    METADATA_FIELDS = {
        "Last Updated": r"\*Last Updated:?\s*(.*?)\*",
        "Owner": r"\*Owner:?\s*(.*?)\*",
        "Status": r"\*Status:?\s*(.*?)\*",
    }

    # Valid status values
    VALID_STATUSES = {
        "Draft",
        "In Progress",
        "Review",
        "Approved",
        "Active",
        "Archived",
        "Deprecated",
    }

    def __init__(
        self,
        owner: str = "Documentation Team",
        status: str = "Draft",
        force: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the metadata updater."""
        self.owner = owner
        self.status = status if status in self.VALID_STATUSES else "Draft"
        self.force = force
        self.dry_run = dry_run
        self.today = datetime.date.today().strftime("%Y-%m-%d")
        self.updated_files: List[str] = []
        self.error_files: List[Tuple[str, str]] = []
        self.skipped_files: List[str] = []

    def update_file(self, file_path: str) -> bool:
        """Update metadata in a single file."""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                self.error_files.append((file_path, "File does not exist"))
                return False

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if file already has metadata
            existing_metadata = self._extract_existing_metadata(content)
            has_metadata = len(existing_metadata) > 0

            if has_metadata and not self.force:
                logger.info(f"File already has metadata (use --force to update): {file_path}")
                self.skipped_files.append(file_path)
                return False

            # Find the title (first h1 heading)
            title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
            if not title_match:
                logger.warning(f"No title (# heading) found in {file_path}")
                title_pos = 0  # Insert at beginning if no title
            else:
                title_pos = title_match.end()

            # Prepare new metadata
            new_metadata = self._generate_metadata(existing_metadata)

            # Insert metadata after title
            if has_metadata:
                # Replace existing metadata
                patterns = [pattern for _, pattern in self.METADATA_FIELDS.items()]
                combined_pattern = r"\n\s*".join(patterns)
                updated_content = re.sub(
                    combined_pattern, new_metadata, content, flags=re.MULTILINE
                )

                # If the pattern didn't match, try a more general approach
                if updated_content == content:
                    metadata_block = re.search(
                        r"^# .+\n\n(\*.+\*\n\*.+\*\n\*.+\*\n)", content, re.MULTILINE
                    )
                    if metadata_block:
                        updated_content = content.replace(metadata_block.group(1), new_metadata)
            else:
                # Insert new metadata after title
                updated_content = (
                    content[:title_pos] + f"\n\n{new_metadata}\n" + content[title_pos:]
                )

            # Don't modify file in dry run mode
            if self.dry_run:
                logger.info(f"[DRY RUN] Would update metadata in: {file_path}")
                return True

            # Write updated content back to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            logger.info(f"Updated metadata in: {file_path}")
            self.updated_files.append(file_path)
            return True

        except Exception as e:
            logger.error(f"Error updating {file_path}: {str(e)}")
            self.error_files.append((file_path, str(e)))
            return False

    def update_directory(self, directory_path: str) -> Dict:
        """Update metadata in all markdown files in a directory and its
        subdirectories.
        """
        md_files = self._find_markdown_files(directory_path)
        total = len(md_files)
        updated = 0

        for i, file_path in enumerate(md_files):
            if self.update_file(file_path):
                updated += 1
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i+1}/{total} files...")

        return {
            "total": total,
            "updated": updated,
            "errors": len(self.error_files),
            "skipped": len(self.skipped_files),
        }

    def generate_report(self, report_path: Optional[str] = None) -> str:
        """Generate a report of all updates."""
        report = "# Metadata Update Report\n\n"
        report += f"**Date:** {self.today}\n\n"
        report += f"**Total Processed:** {len(self.updated_files) + len(self.error_files) + len(self.skipped_files)}\n"
        report += f"**Updated:** {len(self.updated_files)}\n"
        report += f"**Errors:** {len(self.error_files)}\n"
        report += f"**Skipped:** {len(self.skipped_files)}\n\n"

        if self.updated_files:
            report += "## Updated Files\n\n"
            for file in self.updated_files:
                report += f"- {file}\n"
            report += "\n"

        if self.error_files:
            report += "## Errors\n\n"
            for file, error in self.error_files:
                report += f"- {file}: {error}\n"
            report += "\n"

        if self.skipped_files:
            report += "## Skipped Files\n\n"
            for file in self.skipped_files:
                report += f"- {file}\n"

        if report_path:
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report)
                logger.info(f"Report saved to: {report_path}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")

        return report

    def _extract_existing_metadata(self, content: str) -> Dict[str, str]:
        """Extract existing metadata from content."""
        metadata = {}
        for field, pattern in self.METADATA_FIELDS.items():
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                metadata[field] = match.group(1).strip()
        return metadata

    def _generate_metadata(self, existing_metadata: Dict[str, str]) -> str:
        """Generate metadata text."""
        metadata = {
            "Last Updated": self.today,
            "Owner": self.owner,
            "Status": self.status,
        }

        # Keep existing values if not forced to change
        if not self.force:
            for field, value in existing_metadata.items():
                metadata[field] = value

        # Format the metadata
        return (
            f"*Last Updated: {metadata['Last Updated']}*  \n"
            f"*Owner: {metadata['Owner']}*  \n"
            f"*Status: {metadata['Status']}*"
        )

    def _find_markdown_files(self, directory_path: str) -> List[str]:
        """Find all markdown files in a directory and its subdirectories."""
        md_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith((".md", ".markdown")):
                    md_files.append(os.path.join(root, file))
        return md_files

def main():
    parser = argparse.ArgumentParser(description="Update metadata in markdown documentation files")
    parser.add_argument("path", help="File or directory to process")
    parser.add_argument("--owner", default="Documentation Team", help="Document owner")
    parser.add_argument(
        "--status",
        default="Draft",
        choices=[
            "Draft",
            "In Progress",
            "Review",
            "Approved",
            "Active",
            "Archived",
            "Deprecated",
        ],
        help="Document status",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing metadata")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without modifying files"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all markdown files in directory and subdirectories",
    )
    parser.add_argument("--report", help="Save report to specified file")
    parser.add_argument("--quiet", action="store_true", help="Suppress console output")

    args = parser.parse_args()

    # Configure logging
    if args.quiet:
        logger.setLevel(logging.WARNING)

    # Create metadata updater
    updater = MetadataUpdater(
        owner=args.owner, status=args.status, force=args.force, dry_run=args.dry_run
    )

    # Process files
    if args.batch or os.path.isdir(args.path):
        stats = updater.update_directory(args.path)
        logger.info(
            f"Processed {stats['total']} files: {stats['updated']} updated, {stats['errors']} errors, {stats['skipped']} skipped"
        )
    else:
        updater.update_file(args.path)

    # Generate report
    report_path = args.report
    if not report_path and not args.quiet:
        report = updater.generate_report()
        if not args.dry_run:
            print("\n" + report)
    else:
        updater.generate_report(report_path)

if __name__ == "__main__":
    main()
