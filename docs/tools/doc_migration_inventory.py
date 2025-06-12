#!/usr/bin/env python3
"""Document Migration Inventory Tool.

This script helps with the documentation migration process by:
1. Scanning all directories for Markdown files
2. Creating an inventory of markdown files with metadata
3. Identifying potential duplicates based on title similarity
4. Generating recommendations for target locations in the new structure
5. Creating a CSV or JSON report with migration recommendations.
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("doc_migration")

class DocMigrationInventory:
    """Class to handle document migration inventory process."""

    def __init__(
        self,
        root_dir=None,
        output_format="json",
        output_file=None,
        similarity_threshold=0.8,
        ignore_dirs=None,
    ):
        """Initialize the document migration inventory tool.

        Args:
            root_dir (str): Root directory to scan (default: current directory)
            output_format (str): Format for the report ('json' or 'csv')
            output_file (str): Output file path
            similarity_threshold (float): Threshold for determining title similarity (0.0-1.0)
            ignore_dirs (list): List of directory paths to ignore during scan.

        """
        self.root_dir = Path(root_dir or os.getcwd())
        self.output_format = output_format.lower()
        self.output_file = (
            output_file or f"doc_migration_inventory_{int(time.time())}.{self.output_format}"
        )
        self.similarity_threshold = similarity_threshold
        self.ignore_dirs = [Path(d).resolve() for d in (ignore_dirs or [])]

        # Add node_modules to ignored dirs if not already included
        node_modules = Path(self.root_dir) / "node_modules"
        if node_modules.resolve() not in self.ignore_dirs:
            self.ignore_dirs.append(node_modules.resolve())

        self.markdown_files = []
        self.potential_duplicates = []
        self.target_recommendations = {}

        # Content structure patterns
        self.content_patterns = {
            "architecture": r"(architect|system.+design|high.?level.+design|HLD|technical.+design|infrastructure)",
            "guide": r"(guide|tutorial|how.to|walkthrough|instructions)",
            "api": r"(api|endpoint|interface|swagger|openapi)",
            "workflow": r"(workflow|process|procedures|steps)",
            "development": r"(develop|coding|implementation|code)",
            "operations": r"(operations|maintenance|deployment|devops)",
            "project": r"(project|plan|timeline|roadmap|schedule)",
            "security": r"(security|auth|authentication|authorization|threat)",
            "testing": r"(test|qa|quality|verification|validation)",
        }

    def scan_markdown_files(self):
        """Scan all directories for Markdown files and collect metadata."""
        logger.info(f"Scanning for Markdown files in {self.root_dir}")
        try:
            for root, dirs, files in os.walk(self.root_dir, topdown=True):
                # Skip ignored directories
                current_path = Path(root).resolve()
                if any(
                    ignored in current_path.parents or ignored == current_path
                    for ignored in self.ignore_dirs
                ):
                    dirs[:] = []  # Don't descend into ignored directories
                    continue

                # Process markdown files
                for file in files:
                    if file.lower().endswith((".md", ".markdown")):
                        file_path = Path(root) / file
                        try:
                            # Get file metadata
                            stat = file_path.stat()
                            file_size = stat.st_size
                            mod_time = datetime.fromtimestamp(stat.st_mtime)

                            # Extract title from file content or use filename
                            title = self._extract_title(file_path)
                            if not title:
                                title = file_path.stem.replace("_", " ").replace("-", " ").title()

                            # Calculate content hash for duplicates detection
                            content_hash = self._calculate_file_hash(file_path)

                            # Calculate content type signals
                            content_signals = self._analyze_content_signals(file_path)

                            doc_info = {
                                "path": str(file_path.relative_to(self.root_dir)),
                                "title": title,
                                "size_bytes": file_size,
                                "last_modified": mod_time.isoformat(),
                                "content_hash": content_hash,
                                "content_signals": content_signals,
                            }
                            self.markdown_files.append(doc_info)
                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {e}")

            logger.info(f"Found {len(self.markdown_files)} Markdown files")
            return self.markdown_files
        except Exception as e:
            logger.error(f"Error scanning Markdown files: {e}")
            return []

    def identify_duplicates(self):
        """Identify potential duplicates based on title similarity and content
        hash.
        """
        logger.info("Identifying potential duplicates")
        try:
            # Group files by content hash
            hash_groups = defaultdict(list)
            for doc in self.markdown_files:
                hash_groups[doc["content_hash"]].append(doc)

            # Exact duplicates (same content hash)
            exact_duplicates = {h: docs for h, docs in hash_groups.items() if len(docs) > 1}

            # Title similarity detection
            potential_duplicates = []

            # First, add exact duplicates
            for hash_val, docs in exact_duplicates.items():
                dup_set = {"type": "exact_duplicate", "hash": hash_val, "files": docs}
                potential_duplicates.append(dup_set)

            # Then check for similar titles
            processed_indices = set()
            for i, doc1 in enumerate(self.markdown_files):
                if i in processed_indices:
                    continue

                similar_docs = []
                for j, doc2 in enumerate(self.markdown_files[i + 1 :], i + 1):
                    if j in processed_indices:
                        continue

                    # Skip if they're already identified as exact duplicates
                    if doc1["content_hash"] == doc2["content_hash"]:
                        continue

                    similarity = SequenceMatcher(None, doc1["title"], doc2["title"]).ratio()
                    if similarity >= self.similarity_threshold:
                        if not similar_docs:
                            similar_docs.append(doc1)
                        similar_docs.append(doc2)
                        processed_indices.add(j)

                if similar_docs:
                    dup_set = {
                        "type": "similar_title",
                        "similarity_threshold": self.similarity_threshold,
                        "files": similar_docs,
                    }
                    potential_duplicates.append(dup_set)
                    processed_indices.add(i)

            self.potential_duplicates = potential_duplicates
            logger.info(f"Found {len(potential_duplicates)} sets of potential duplicates")
            return potential_duplicates
        except Exception as e:
            logger.error(f"Error identifying duplicates: {e}")
            return []

    def generate_recommendations(self):
        """Generate recommendations for target locations in the new
        structure.
        """
        logger.info("Generating target location recommendations")
        try:
            recommendations = {}

            for doc in self.markdown_files:
                # Determine recommended location based on content signals
                signals = doc["content_signals"]

                # Get the top signal category
                top_category = max(signals.items(), key=lambda x: x[1], default=(None, 0))

                if top_category[0] and top_category[1] > 0:
                    # Map category to recommended folder structure
                    category_map = {
                        "architecture": "docs/architecture/",
                        "guide": "docs/guides/",
                        "api": "docs/api/",
                        "workflow": "docs/workflows/",
                        "development": "docs/development/",
                        "operations": "docs/operations/",
                        "project": "docs/project/",
                        "security": "docs/security/",
                        "testing": "docs/testing/",
                    }

                    recommended_path = category_map.get(top_category[0], "docs/general/")

                    # For files in potential duplicate sets, add a note
                    duplicate_note = ""
                    for dup_set in self.potential_duplicates:
                        if any(d["path"] == doc["path"] for d in dup_set["files"]):
                            if dup_set["type"] == "exact_duplicate":
                                duplicate_note = "ATTENTION: Exact duplicate content exists"
                            else:
                                duplicate_note = "ATTENTION: Similar document title exists"
                            break

                    recommendations[doc["path"]] = {
                        "recommended_location": recommended_path,
                        "confidence": top_category[1],
                        "duplicate_note": duplicate_note,
                        "secondary_category": self._get_secondary_category(signals),
                    }
                else:
                    # Default recommendation
                    recommendations[doc["path"]] = {
                        "recommended_location": "docs/general/",
                        "confidence": 0,
                        "duplicate_note": "",
                        "secondary_category": None,
                    }

            self.target_recommendations = recommendations
            logger.info(f"Generated recommendations for {len(recommendations)} files")
            return recommendations
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {}

    def create_report(self):
        """Create a CSV or JSON report of the document inventory with migration
        recommendations.
        """
        logger.info(f"Creating {self.output_format} report at {self.output_file}")
        try:
            # Combine inventory and recommendations
            report_data = []
            for doc in self.markdown_files:
                report_entry = doc.copy()
                report_entry.update(self.target_recommendations.get(doc["path"], {}))
                report_data.append(report_entry)

            # Write to file
            if self.output_format == "json":
                with open(self.output_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "generated_at": datetime.now().isoformat(),
                            "total_documents": len(report_data),
                            "root_directory": str(self.root_dir),
                            "documents": report_data,
                            "potential_duplicates": self.potential_duplicates,
                        },
                        f,
                        indent=2,
                    )
            elif self.output_format == "csv":
                with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                    fieldnames = [
                        "path",
                        "title",
                        "size_bytes",
                        "last_modified",
                        "recommended_location",
                        "confidence",
                        "duplicate_note",
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for entry in report_data:
                        # Flatten the structure for CSV
                        csv_entry = {
                            "path": entry["path"],
                            "title": entry["title"],
                            "size_bytes": entry["size_bytes"],
                            "last_modified": entry["last_modified"],
                            "recommended_location": entry.get("recommended_location", ""),
                            "confidence": entry.get("confidence", 0),
                            "duplicate_note": entry.get("duplicate_note", ""),
                        }
                        writer.writerow(csv_entry)

            logger.info(f"Report created successfully at {self.output_file}")
            return self.output_file
        except Exception as e:
            logger.error(f"Error creating report: {e}")
            return None

    def _extract_title(self, file_path):
        """Extract title from markdown file (from first heading or front
        matter).
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

                # Try to extract from front matter
                front_matter_match = re.search(r"^---\s+(.*?)\s+---", content, re.DOTALL)
                if front_matter_match:
                    front_matter = front_matter_match.group(1)
                    title_match = re.search(
                        r'title:\s*[\'"]?(.*?)[\'"]?\s*$', front_matter, re.MULTILINE
                    )
                    if title_match:
                        return title_match.group(1).strip()

                # Try to extract from first heading
                heading_match = re.search(r"^#\s+(.*?)$", content, re.MULTILINE)
                if heading_match:
                    return heading_match.group(1).strip()

                return None
        except Exception as e:
            logger.warning(f"Could not extract title from {file_path}: {e}")
            return None

    def _calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of file content for duplicate detection."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return None

    def _analyze_content_signals(self, file_path):
        """Analyze content of the file to determine its type/category."""
        signals = {category: 0 for category in self.content_patterns}

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().lower()

                # Check for signals in the content
                for category, pattern in self.content_patterns.items():
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    signals[category] = len(matches)

                # Boost signal based on file path
                path_str = str(file_path).lower()
                for category in signals:
                    if category in path_str:
                        signals[category] += 2
        except Exception as e:
            logger.warning(f"Could not analyze content signals for {file_path}: {e}")

        return signals

    def _get_secondary_category(self, signals):
        """Get the secondary category from content signals."""
        if not signals:
            return None

        # Sort signals by value (descending) and get the second one if it exists
        sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_signals) > 1 and sorted_signals[1][1] > 0:
            return sorted_signals[1][0]
        return None

    def run_full_process(self):
        """Run the full document migration inventory process."""
        logger.info("Starting document migration inventory process")
        self.scan_markdown_files()
        self.identify_duplicates()
        self.generate_recommendations()
        report_file = self.create_report()
        logger.info("Document migration inventory process completed")
        return report_file

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description="Document Migration Inventory Tool")
    parser.add_argument("--root-dir", type=str, help="Root directory to scan")
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "csv"],
        default="json",
        help="Output format (json or csv)",
    )
    parser.add_argument("--output-file", type=str, help="Output file path")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.8,
        help="Threshold for determining title similarity (0.0-1.0)",
    )
    parser.add_argument(
        "--ignore-dirs",
        type=str,
        nargs="+",
        help="List of directory paths to ignore during scan",
    )

    args = parser.parse_args()

    # Run the inventory process
    inventory = DocMigrationInventory(
        root_dir=args.root_dir,
        output_format=args.output_format,
        output_file=args.output_file,
        similarity_threshold=args.similarity_threshold,
        ignore_dirs=args.ignore_dirs,
    )

    report_file = inventory.run_full_process()

    if report_file:
        print(f"\nReport generated successfully: {report_file}")
        print(f"Found {len(inventory.markdown_files)} markdown files")
        print(f"Identified {len(inventory.potential_duplicates)} sets of potential duplicates")
        print(f"Generated recommendations for {len(inventory.target_recommendations)} files")
    else:
        print("Failed to generate report. Check the logs for details.")

if __name__ == "__main__":
    main()
