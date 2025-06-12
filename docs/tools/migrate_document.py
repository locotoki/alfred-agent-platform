#!/usr/bin/env python3
"""Document Migration Tool.

This script automates part of the document migration process by:
1. Copying content from a source document to a target document
2. Applying appropriate templates based on document type
3. Adding required metadata (date, owner, status)
4. Formatting headings to match documentation standards
5. Adding appropriate cross-references
6. Detecting possible duplicates

Requires human review for content decisions.

Usage:
    python migrate_document.py [options] <source_path> <target_path>

Options:
    --type TYPE           Document type (agent, workflow, project, architecture, guide, api)
    --owner OWNER         Document owner (default: current user)
    --status STATUS       Document status (draft, review, approved) (default: draft)
    --check-duplicates    Check for potential duplicates
    --verbose             Show detailed output
    --dry-run             Show what would happen without making changes
    --help                Show this help message

Examples:
    # Migrate a document with automatic type detection
    python migrate_document.py old_docs/agent_x.md new_docs/agents/agent_x.md

    # Migrate a document with specific type and owner
    python migrate_document.py old_docs/workflow.md new_docs/workflows/workflow.md --type workflow --owner "Jane Doe"

    # Check for duplicates before migration
    python migrate_document.py old_docs/guide.md new_docs/guides/guide.md --check-duplicates

"""

import argparse
import difflib
import getpass
import hashlib
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migrate_document")

# Constants for document migration
DOC_TYPES = {
    "agent": "Agent Documentation",
    "workflow": "Workflow Documentation",
    "project": "Project Documentation",
    "architecture": "Architecture Documentation",
    "guide": "User Guide",
    "api": "API Documentation",
    "general": "General Documentation",
}

# Document template patterns
TEMPLATES = {
    "agent": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*Brief description of this agent's purpose and functionality.*

## Configuration
*How to configure and set up this agent.*

## Inputs
*The inputs this agent accepts.*

## Outputs
*The outputs this agent produces.*

## Integration Points
*How this agent connects with other components or systems.*

## Examples
*Example usage and configuration.*

## Troubleshooting
*Common issues and their solutions.*

## Related Documents
{cross_references}.
""",
    "workflow": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*Brief description of this workflow's purpose.*

## Prerequisites
*Required setup before using this workflow.*

## Steps
*Detailed workflow steps.*

## Inputs and Outputs
*The inputs and outputs for this workflow.*

## Examples
*Example usage scenarios.*

## Related Documents
{cross_references}.
""",
    "project": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Project Overview
*Brief description of this project.*

## Goals and Objectives
*What this project aims to accomplish.*

## Timeline
*Key milestones and dates.*

## Resources
*Team members, budget, tools, etc.*

## Deliverables
*Expected project outputs.*

## Related Documents
{cross_references}.
""",
    "architecture": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*High-level description of this architecture.*

## Components
*Main architectural components.*

## Data Flow
*How data flows through the system.*

## Integration Points
*System interfaces and integration.*

## Non-Functional Requirements
*Performance, security, scalability considerations.*

## Related Documents
{cross_references}.
""",
    "guide": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*Purpose of this guide.*

## Prerequisites
*What you need before starting.*

## Instructions
*Step-by-step guide.*

## Tips and Best Practices
*Additional recommendations.*

## Troubleshooting
*Common issues and solutions.*

## Related Documents
{cross_references}.
""",
    "api": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*Brief description of this API.*

## Authentication
*How to authenticate with this API.*

## Endpoints
*Available API endpoints.*

## Request/Response Format
*Structure of requests and responses.*

## Examples
*Sample API calls and responses.*

## Error Handling
*Error codes and troubleshooting.*

## Related Documents
{cross_references}.
""",
    "general": """# {title}

**Last Updated:** {date}
**Owner:** {owner}
**Status:** {status}

## Overview
*Brief description of this document.*

## Content

## Related Documents
{cross_references}.
""",
}

# Regex patterns for parsing markdown documents
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
METADATA_PATTERN = re.compile(r"\*\*([^:]+):\*\*\s*(.*?)(?:\s{2,}|\n)", re.MULTILINE)
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

class DocumentMigrator:
    """Handles the migration of documentation from one location to another with
    formatting, templates, and metadata additions.
    """

    def __init__(
        self,
        source_path: str,
        target_path: str,
        doc_type: Optional[str] = None,
        owner: Optional[str] = None,
        status: str = "draft",
        check_duplicates: bool = False,
        verbose: bool = False,
        dry_run: bool = False,
    ):
        """Initialize the document migrator.

        Args:
            source_path: Path to the source document
            target_path: Path to the target document
            doc_type: Document type (agent, workflow, etc.)
            owner: Document owner
            status: Document status (draft, review, approved)
            check_duplicates: Whether to check for potential duplicates
            verbose: Whether to show detailed output
            dry_run: Whether to perform a dry run (no changes).

        """
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)
        self.doc_type = doc_type
        self.owner = owner or getpass.getuser()
        self.status = status
        self.check_duplicates = check_duplicates
        self.verbose = verbose
        self.dry_run = dry_run

        # Will be populated during migration
        self.source_content = ""
        self.target_content = ""
        self.title = ""
        self.metadata = {}
        self.cross_references = []

    def validate_inputs(self) -> bool:
        """Validate that source exists and target directory is writable.

        Returns:
            bool: True if validation passed, False otherwise.

        """
        # Check source file exists
        if not self.source_path.exists() or not self.source_path.is_file():
            logger.error(f"Source file does not exist: {self.source_path}")
            return False

        # Check source is markdown
        if self.source_path.suffix.lower() not in [".md", ".markdown"]:
            logger.error(f"Source file is not a markdown file: {self.source_path}")
            return False

        # Check target directory exists or can be created
        target_dir = self.target_path.parent
        if not target_dir.exists():
            try:
                if not self.dry_run:
                    target_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created target directory: {target_dir}")
            except Exception as e:
                logger.error(f"Cannot create target directory {target_dir}: {e}")
                return False

        # Ensure target has correct extension
        if self.target_path.suffix.lower() not in [".md", ".markdown"]:
            self.target_path = self.target_path.with_suffix(".md")
            logger.info(f"Adjusted target path to ensure markdown extension: {self.target_path}")

        # Check target directory is writable
        if target_dir.exists() and not os.access(target_dir, os.W_OK):
            logger.error(f"Target directory is not writable: {target_dir}")
            return False

        # Validate document type if provided
        if self.doc_type and self.doc_type not in DOC_TYPES:
            logger.error(
                f"Invalid document type: {self.doc_type}. Must be one of {list(DOC_TYPES.keys())}"
            )
            return False

        return True

    def read_source(self) -> bool:
        """Read the content of the source document.

        Returns:
            bool: True if successful, False otherwise.

        """
        try:
            with open(self.source_path, "r", encoding="utf-8") as f:
                self.source_content = f.read()

            if self.verbose:
                logger.info(f"Read {len(self.source_content)} bytes from {self.source_path}")
            return True
        except Exception as e:
            logger.error(f"Error reading source file: {e}")
            return False

    def extract_metadata(self) -> Dict[str, str]:
        """Extract metadata from the source document.

        Returns:
            Dict containing metadata fields and values.

        """
        metadata = {}

        # Extract title from first heading
        title_match = TITLE_PATTERN.search(self.source_content)
        if title_match:
            self.title = title_match.group(1).strip()
            metadata["Title"] = self.title
        else:
            # Use filename as title if no heading found
            self.title = self.source_path.stem.replace("_", " ").replace("-", " ").title()
            metadata["Title"] = self.title
            logger.warning(f"No title found in document, using filename: {self.title}")

        # Extract metadata fields
        metadata_matches = METADATA_PATTERN.finditer(self.source_content)
        for match in metadata_matches:
            key = match.group(1).strip()
            value = match.group(2).strip()
            metadata[key] = value

        if self.verbose:
            logger.info(f"Extracted metadata: {metadata}")

        self.metadata = metadata
        return metadata

    def detect_document_type(self) -> str:
        """Detect the document type based on content and path.

        Returns:
            Detected document type.

        """
        if self.doc_type:
            return self.doc_type

        # Content patterns to detect document type
        content_patterns = {
            "agent": r"(agent|bot|automation|AI assistant)",
            "workflow": r"(workflow|process|procedures|steps)",
            "project": r"(project|plan|timeline|roadmap|schedule)",
            "architecture": r"(architect|system.+design|high.?level.+design|HLD|technical.+design|infrastructure)",
            "guide": r"(guide|tutorial|how.to|walkthrough|instructions)",
            "api": r"(api|endpoint|interface|swagger|openapi)",
        }

        # Check path first
        path_str = str(self.source_path).lower()
        for doc_type in content_patterns:
            if doc_type in path_str:
                if self.verbose:
                    logger.info(f"Detected document type from path: {doc_type}")
                return doc_type

        # Check content
        content_lower = self.source_content.lower()
        type_scores = {}

        for doc_type, pattern in content_patterns.items():
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            type_scores[doc_type] = len(matches)

        # Get highest scoring type
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                if self.verbose:
                    logger.info(
                        f"Detected document type from content: {best_type[0]} (score: {best_type[1]})"
                    )
                return best_type[0]

        # Default to general
        logger.info("Could not detect specific document type, using 'general'")
        return "general"

    def format_headings(self) -> str:
        """Format headings to match documentation standards.

        Returns:
            Content with reformatted headings.

        """
        content = self.source_content

        # Find all headings
        headings = HEADING_PATTERN.finditer(content)
        replacements = []

        for match in headings:
            heading_level = match.group(1)
            heading_text = match.group(2).strip()

            # Format heading text (sentence case)
            if heading_text and not heading_text[0].isupper():
                new_heading_text = heading_text[0].upper() + heading_text[1:]
                new_heading = f"{heading_level} {new_heading_text}"
                replacements.append((match.group(0), new_heading))

        # Apply replacements in reverse order to prevent messing up positions
        for old, new in reversed(replacements):
            content = content.replace(old, new)

        if len(replacements) > 0 and self.verbose:
            logger.info(f"Reformatted {len(replacements)} headings")

        return content

    def extract_cross_references(self) -> List[str]:
        """Extract cross-references from the document.

        Returns:
            List of cross-reference links.

        """
        links = LINK_PATTERN.finditer(self.source_content)
        references = []

        for match in links:
            link_text = match.group(1)
            link_target = match.group(2)

            # Skip external links and anchors
            if link_target.startswith(("http://", "https://", "mailto:", "#")):
                continue

            references.append(f"- [{link_text}]({link_target})")

        if self.verbose:
            logger.info(f"Found {len(references)} cross-references")

        self.cross_references = references
        return references

    def create_target_content(self) -> str:
        """Create content for the target document using appropriate template.

        Returns:
            Formatted content for target document.

        """
        # Detect document type if not specified
        doc_type = self.detect_document_type()

        # Format date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Use metadata from source where available, or use provided values
        owner = self.metadata.get("Owner", self.owner)
        status = self.metadata.get("Status", self.status)

        # Format cross-references
        cross_refs = "\n".join(self.cross_references) if self.cross_references else "*None*"

        # Get template based on document type
        template = TEMPLATES.get(doc_type, TEMPLATES["general"])

        # Apply template
        target_content = template.format(
            title=self.title,
            date=current_date,
            owner=owner,
            status=status,
            cross_references=cross_refs,
        )

        # For migration, we want to preserve content from source
        # but apply the template structure

        # Extract content section from template (everything between Overview and Related Documents)
        template_sections = re.split(r"^##\s+.+$", template, flags=re.MULTILINE)

        # Extract content from source (everything after the title)
        source_content_parts = re.split(
            r"^#\s+.+$", self.source_content, maxsplit=1, flags=re.MULTILINE
        )
        source_content_body = (
            source_content_parts[1].strip() if len(source_content_parts) > 1 else ""
        )

        # Format source content headings
        source_content_body = self.format_headings()

        # Find the "Related Documents" section in the template
        related_docs_index = target_content.find("## Related Documents")

        if related_docs_index > 0:
            # Insert the formatted source content before the Related Documents section
            target_content = (
                target_content[:related_docs_index]
                + "\n\n"
                + source_content_body
                + "\n\n"
                + target_content[related_docs_index:]
            )
        else:
            target_content += "\n\n" + source_content_body

        self.target_content = target_content
        return target_content

    def check_for_duplicates(self) -> List[Dict[str, Any]]:
        """Check for potential duplicate documents based on title and content
        similarity.

        Returns:
            List of potential duplicate documents with similarity scores.

        """
        if not self.check_duplicates:
            return []

        potential_duplicates = []
        docs_dir = self.target_path.parent.parent  # Assuming standard docs structure

        # Scan for markdown files in the docs directory
        if docs_dir.exists() and docs_dir.is_dir():
            markdown_files = list(docs_dir.glob("**/*.md"))

            # Calculate hash of source content for exact matches
            source_hash = hashlib.sha256(self.source_content.encode("utf-8")).hexdigest()

            for file_path in markdown_files:
                # Skip the source file itself
                if file_path.samefile(self.source_path):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Check for exact content match
                    file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    if file_hash == source_hash:
                        potential_duplicates.append(
                            {
                                "path": str(file_path),
                                "similarity": 1.0,
                                "type": "exact_match",
                            }
                        )
                        continue

                    # Check title similarity
                    title_match = TITLE_PATTERN.search(content)
                    if title_match:
                        file_title = title_match.group(1).strip()
                        title_similarity = difflib.SequenceMatcher(
                            None, self.title, file_title
                        ).ratio()

                        if title_similarity > 0.8:  # 80% similarity threshold
                            potential_duplicates.append(
                                {
                                    "path": str(file_path),
                                    "similarity": title_similarity,
                                    "type": "title_similarity",
                                    "title": file_title,
                                }
                            )

                    # Check content similarity (simple but effective approach)
                    content_similarity = difflib.SequenceMatcher(
                        None, self.source_content, content
                    ).ratio()
                    if content_similarity > 0.7:  # 70% similarity threshold
                        potential_duplicates.append(
                            {
                                "path": str(file_path),
                                "similarity": content_similarity,
                                "type": "content_similarity",
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error checking file {file_path} for duplicates: {e}")

        if self.verbose:
            logger.info(f"Found {len(potential_duplicates)} potential duplicate documents")

        return potential_duplicates

    def write_target(self) -> bool:
        """Write the migrated content to the target file.

        Returns:
            bool: True if successful, False otherwise.

        """
        if self.dry_run:
            logger.info("Dry run - not writing target file")
            return True

        try:
            # Create parent directories if they don't exist
            self.target_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.target_path, "w", encoding="utf-8") as f:
                f.write(self.target_content)

            logger.info(f"Successfully wrote migrated document to {self.target_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing target file: {e}")
            return False

    def migrate(self) -> Dict[str, Any]:
        """Perform the full document migration process.

        Returns:
            Dict containing migration results and metadata.

        """
        logger.info(f"Starting migration from {self.source_path} to {self.target_path}")

        # Validate inputs
        if not self.validate_inputs():
            return {"success": False, "error": "Input validation failed"}

        # Read source document
        if not self.read_source():
            return {"success": False, "error": "Failed to read source document"}

        # Extract metadata
        self.extract_metadata()

        # Extract cross-references
        self.extract_cross_references()

        # Check for duplicates if requested
        potential_duplicates = []
        if self.check_duplicates:
            potential_duplicates = self.check_for_duplicates()
            if potential_duplicates:
                logger.warning(f"Found {len(potential_duplicates)} potential duplicates")

        # Create target content
        self.create_target_content()

        # Write target document
        success = self.write_target()

        # Return migration results
        return {
            "success": success,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "doc_type": self.detect_document_type(),
            "title": self.title,
            "metadata": self.metadata,
            "potential_duplicates": potential_duplicates,
            "dry_run": self.dry_run,
        }

def print_migration_report(result: Dict[str, Any]):
    """Print a formatted report of the migration result."""
    print("\n" + "=" * 80)
    print("DOCUMENT MIGRATION REPORT")
    print("=" * 80)

    if result.get("success", False):
        print("Status: ✅ SUCCESS")
    else:
        print(f"Status: ❌ FAILED - {result.get('error', 'Unknown error')}")
        return

    print(f"\nSource: {result['source_path']}")
    print(f"Target: {result['target_path']}")
    print(f"Document Type: {result['doc_type']}")
    print(f"Title: {result['title']}")

    print("\nMetadata:")
    for key, value in result.get("metadata", {}).items():
        print(f"  - {key}: {value}")

    duplicates = result.get("potential_duplicates", [])
    if duplicates:
        print("\n⚠️  POTENTIAL DUPLICATES DETECTED:")
        for dup in duplicates:
            sim_percent = int(dup["similarity"] * 100)
            dup_type = dup["type"].replace("_", " ").title()
            print(f"  - {dup['path']} - {sim_percent}% similarity ({dup_type})")
            if "title" in dup:
                print(f"    Title: \"{dup['title']}\"")
        print("\nPlease review these potential duplicates before proceeding.")

    if result.get("dry_run", False):
        print("\n📝 NOTE: This was a dry run. No files were modified.")

    print("\nMigration completed successfully!")
    print("=" * 80)

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Document Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("source", help="Source document path")
    parser.add_argument("target", help="Target document path")
    parser.add_argument("--type", choices=DOC_TYPES.keys(), help="Document type")
    parser.add_argument("--owner", help="Document owner (default: current user)")
    parser.add_argument(
        "--status",
        default="draft",
        choices=["draft", "review", "approved"],
        help="Document status (default: draft)",
    )
    parser.add_argument(
        "--check-duplicates", action="store_true", help="Check for potential duplicates"
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )

    args = parser.parse_args()

    # Initialize the document migrator
    migrator = DocumentMigrator(
        source_path=args.source,
        target_path=args.target,
        doc_type=args.type,
        owner=args.owner,
        status=args.status,
        check_duplicates=args.check_duplicates,
        verbose=args.verbose,
        dry_run=args.dry_run,
    )

    # Perform migration
    result = migrator.migrate()

    # Print report
    print_migration_report(result)

    # Return appropriate exit code
    sys.exit(0 if result.get("success", False) else 1)

if __name__ == "__main__":
    main()
