#!/usr/bin/env python3
"""Document Consolidation Tool.

This script consolidates documents from the staging area into the main
documentation structure following the guidelines in the Document
Consolidation Guide.
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("consolidate_docs")

class DocumentConsolidator:
    """Class to handle document consolidation process."""

    def __init__(
        self,
        staging_dir=None,
        target_dir=None,
        inventory_file=None,
        group=None,
        dry_run=True,
    ):
        """Initialize the document consolidator.

        Args:
            staging_dir (str): Path to the staging area directory
            target_dir (str): Path to the target directory for consolidated docs
            inventory_file (str): Path to the inventory JSON file
            group (str): Group to consolidate (e.g., "rag", "infra", "all")
            dry_run (bool): If True, only show what would be done without actually consolidating

        """
        self.staging_dir = Path(staging_dir or "")
        self.target_dir = Path(target_dir or "")
        self.inventory_file = inventory_file
        self.group = group
        self.dry_run = dry_run

        # Load inventory data if available
        self.inventory_data = None
        if inventory_file and os.path.exists(inventory_file):
            with open(inventory_file, "r", encoding="utf-8") as f:
                self.inventory_data = json.load(f)

        # Define consolidation groups
        self.consolidation_groups = {
            "rag": {
                "source_pattern": r"rag.*\.md$",
                "target_dir": "projects/rag-service",
                "primary_doc": "rag-service.md",
                "target_doc": "README.md",
            },
            "infra": {
                "source_pattern": r"(infrastructure|infra).*\.md$",
                "target_dir": "infrastructure-crew",
                "primary_doc": "infrastructure-crew.md",
                "target_doc": "README.md",
            },
            "platform": {
                "source_pattern": r"ai-agent-platform.*\.md$",
                "target_dir": "project",
                "primary_doc": "ai-agent-platform-v2-master-project-plan.md",
                "target_doc": "master-plan.md",
            },
            "social": {
                "source_pattern": r"social.*\.md$",
                "target_dir": "agents",
                "primary_doc": "social-intel-agent.md",
                "target_doc": "social-intelligence-agent.md",
            },
            "alfred": {
                "source_pattern": r"alfred.*\.md$",
                "target_dir": "alfred_assistant_implementation",
                "primary_doc": "alfred-home-comprehensive-deployment-guide.md",
                "target_doc": "implementation-plan.md",
            },
        }

    def consolidate_documents(self):
        """Consolidate documents from staging area to target directories.

        Returns:
            dict: Statistics of consolidated files.

        """
        if not self.staging_dir.exists():
            logger.error(f"Staging directory does not exist: {self.staging_dir}")
            return {"consolidated": 0, "skipped": 0, "errors": 1}

        logger.info("Starting document consolidation process")
        logger.info(f"Staging directory: {self.staging_dir}")
        logger.info(f"Target directory: {self.target_dir}")
        logger.info(f"Dry run: {self.dry_run}")

        # Determine which groups to process
        groups_to_process = []
        if self.group == "all":
            groups_to_process = list(self.consolidation_groups.keys())
        elif self.group in self.consolidation_groups:
            groups_to_process = [self.group]
        else:
            logger.error(f"Unknown consolidation group: {self.group}")
            return {"consolidated": 0, "skipped": 0, "errors": 1}

        # Process each group
        stats = {"consolidated": 0, "skipped": 0, "errors": 0}
        for group_name in groups_to_process:
            group_stats = self._consolidate_group(group_name)
            for key in stats:
                stats[key] += group_stats.get(key, 0)

        return stats

    def _consolidate_group(self, group_name):
        """Consolidate a specific group of documents.

        Args:
            group_name (str): Name of the consolidation group

        Returns:
            dict: Statistics for this group.

        """
        group_info = self.consolidation_groups[group_name]
        source_pattern = re.compile(group_info["source_pattern"])
        target_dir_path = self.target_dir / group_info["target_dir"]
        primary_doc = group_info["primary_doc"]
        target_doc = group_info["target_doc"]

        logger.info(f"Processing group: {group_name}")
        logger.info(f"Target directory: {target_dir_path}")
        logger.info(f"Primary document: {primary_doc}")
        logger.info(f"Target document: {target_doc}")

        # Find matching files
        matching_files = []
        primary_file_path = None

        for root, _, files in os.walk(self.staging_dir):
            for file in files:
                if not file.endswith(".md"):
                    continue

                if source_pattern.search(file):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.staging_dir)
                    matching_files.append((file_path, rel_path))

                    if file == primary_doc:
                        primary_file_path = file_path

        logger.info(f"Found {len(matching_files)} matching files")

        if not matching_files:
            logger.warning(f"No matching files found for group {group_name}")
            return {"consolidated": 0, "skipped": 0, "errors": 0}

        if not primary_file_path:
            logger.warning(
                f"Primary document {primary_doc} not found, using first matching file instead"
            )
            primary_file_path = matching_files[0][0]

        # Create target directory if it doesn't exist
        if not self.dry_run:
            os.makedirs(target_dir_path, exist_ok=True)

        # Prepare the consolidated document
        target_file_path = target_dir_path / target_doc

        # Simple consolidation in dry run mode
        if self.dry_run:
            logger.info(
                f"DRY RUN: Would consolidate {len(matching_files)} files into {target_file_path}"
            )
            logger.info(f"DRY RUN: Primary document: {primary_file_path}")
            logger.info("DRY RUN: Files to merge:")
            for file_path, rel_path in matching_files:
                if file_path != primary_file_path:
                    logger.info(f"  - {rel_path}")
            return {"consolidated": len(matching_files), "skipped": 0, "errors": 0}

        # Perform actual consolidation
        try:
            # First, copy the primary document as a base
            with open(primary_file_path, "r", encoding="utf-8") as f:
                primary_content = f.read()

            # Add a notice about consolidation
            consolidation_notice = f"""
**Note:** This document is a consolidation of multiple source documents from the staging area.
Last consolidated: {datetime.now().strftime('%Y-%m-%d')}.
"""

            # Create a list of source documents
            source_list = "## Source Documents\n\n"
            for _, rel_path in matching_files:
                source_list += f"- {rel_path}\n"

            # Write the consolidated document
            with open(target_file_path, "w", encoding="utf-8") as f:
                f.write(primary_content)
                f.write("\n\n")
                f.write(consolidation_notice)
                f.write("\n\n")
                f.write(source_list)
                f.write("\n\n")

            logger.info(f"Created consolidated document: {target_file_path}")

            # Copy all original files to a subdirectory for reference
            source_dir = target_dir_path / "source"
            os.makedirs(source_dir, exist_ok=True)

            for file_path, rel_path in matching_files:
                source_file_path = source_dir / rel_path.name
                shutil.copy2(file_path, source_file_path)
                logger.info(f"Copied source file: {rel_path} -> {source_file_path}")

            return {"consolidated": len(matching_files), "skipped": 0, "errors": 0}

        except Exception as e:
            logger.error(f"Error consolidating group {group_name}: {e}")
            return {"consolidated": 0, "skipped": 0, "errors": 1}

    def print_summary(self, stats):
        """Print a summary of the operations performed."""
        logger.info("=== Consolidation Summary ===")
        logger.info(f"Files consolidated: {stats['consolidated']}")
        logger.info(f"Files skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")

        if self.dry_run:
            logger.info("\nThis was a dry run. No files were actually consolidated.")
            logger.info("To actually consolidate files, run without the --dry-run option.")
        else:
            logger.info(f"\nSuccessfully consolidated documents into {self.target_dir}")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Document Consolidation Tool")
    parser.add_argument(
        "--staging-dir",
        type=str,
        default="/home/locotoki/projects/alfred-agent-platform-v2/docs/staging-area",
        help="Path to the staging area directory",
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default="/home/locotoki/projects/alfred-agent-platform-v2/docs",
        help="Path to the target directory for consolidated docs",
    )
    parser.add_argument(
        "--inventory-file",
        type=str,
        help="Path to the inventory JSON file",
    )
    parser.add_argument(
        "--group",
        type=str,
        default="all",
        help="Group to consolidate (e.g., 'rag', 'infra', 'all')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually consolidating files",
    )

    args = parser.parse_args()

    # Run the consolidation process
    consolidator = DocumentConsolidator(
        staging_dir=args.staging_dir,
        target_dir=args.target_dir,
        inventory_file=args.inventory_file,
        group=args.group,
        dry_run=args.dry_run,
    )

    stats = consolidator.consolidate_documents()
    consolidator.print_summary(stats)

if __name__ == "__main__":
    main()
