#!/usr/bin/env python3
"""Normalize Filenames in Staging Area.

This script normalizes filenames in the staging-area directory by:
1. Removing special characters and spaces
2. Converting to lowercase with hyphens as separators
3. Removing hexadecimal suffixes and Zone.Identifier files
4. Creating a mapping file that tracks old and new filenames.
"""

import argparse
import logging
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("normalize_filenames")

class FilenameNormalizer:
    """Class to handle filename normalization process."""

    def __init__(
        self,
        staging_dir=None,
        dry_run=True,
        remove_zone_identifier=True,
        hex_suffix_pattern=r"\s+[0-9a-f]{32}",
        output_mapping="filename_mapping.csv",
    ):
        """Initialize the filename normalizer.

        Args:
            staging_dir (str): Path to the staging-area directory
            dry_run (bool): If True, only show what would be done without actually renaming
            remove_zone_identifier (bool): If True, remove .Zone.Identifier files
            hex_suffix_pattern (str): Regex pattern to match hexadecimal suffixes in filenames
            output_mapping (str): Path to the output mapping file.

        """
        self.staging_dir = Path(staging_dir or "")
        self.dry_run = dry_run
        self.remove_zone_identifier = remove_zone_identifier
        self.hex_suffix_pattern = hex_suffix_pattern
        self.output_mapping = output_mapping
        self.renamed_files = []
        self.removed_files = []
        self.skipped_files = []
        self.errors = []

    def normalize_filename(self, filename):
        """Normalize a filename by removing special characters and converting
        to lowercase with hyphens.

        Args:
            filename (str): The filename to normalize

        Returns:
            str: The normalized filename.

        """
        # Extract the base name and extension
        name, ext = os.path.splitext(filename)

        # Remove hexadecimal suffix if present
        name = re.sub(self.hex_suffix_pattern, "", name)

        # Normalize unicode characters
        name = unicodedata.normalize("NFKD", name)

        # Replace special characters and spaces with hyphens
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"[\s_]+", "-", name)

        # Convert to lowercase and remove leading/trailing hyphens
        name = name.lower().strip("-")

        # Return normalized filename with the original extension
        return f"{name}{ext}"

    def process_directory(self):
        """Process all files in the staging directory and its subdirectories.

        Returns:
            dict: Statistics of processed files.

        """
        if not self.staging_dir.exists():
            logger.error(f"Directory does not exist: {self.staging_dir}")
            return {
                "renamed": 0,
                "removed": 0,
                "skipped": 0,
                "errors": 1,
            }

        logger.info(f"Processing directory: {self.staging_dir}")
        logger.info(f"Dry run: {self.dry_run}")

        # Create a dictionary to store filename mappings by directory
        mappings = defaultdict(list)

        # Walk through all files in the directory
        for root, _, files in os.walk(self.staging_dir):
            root_path = Path(root)

            # Process each file in the current directory
            for filename in files:
                file_path = root_path / filename

                try:
                    # Skip files that don't need renaming or should be removed
                    if self.remove_zone_identifier and filename.endswith(".Zone.Identifier"):
                        if not self.dry_run:
                            os.remove(file_path)
                        self.removed_files.append(str(file_path))
                        continue

                    # Normalize the filename
                    new_filename = self.normalize_filename(filename)

                    # Skip if the filename is already normalized
                    if new_filename == filename:
                        self.skipped_files.append(str(file_path))
                        continue

                    # Create the new file path
                    new_file_path = root_path / new_filename

                    # Check if the new filename already exists
                    if new_file_path.exists():
                        # Find an alternative name by appending a number
                        counter = 1
                        while new_file_path.exists():
                            name, ext = os.path.splitext(new_filename)
                            numbered_filename = f"{name}-{counter}{ext}"
                            new_file_path = root_path / numbered_filename
                            counter += 1

                        new_filename = new_file_path.name

                    # Rename the file if not in dry run mode
                    if not self.dry_run:
                        file_path.rename(new_file_path)

                    # Add to the mapping
                    mappings[str(root_path.relative_to(self.staging_dir))].append(
                        (filename, new_filename)
                    )

                    # Add to the list of renamed files
                    self.renamed_files.append((str(file_path), str(new_file_path)))

                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    self.errors.append((str(file_path), str(e)))

        # Write the mapping file
        self._write_mapping_file(mappings)

        # Return statistics
        return {
            "renamed": len(self.renamed_files),
            "removed": len(self.removed_files),
            "skipped": len(self.skipped_files),
            "errors": len(self.errors),
        }

    def _write_mapping_file(self, mappings):
        """Write the mapping file.

        Args:
            mappings (dict): Dictionary of directory -> list of (old_name, new_name) tuples.

        """
        if self.dry_run:
            logger.info("Dry run: Not writing mapping file")
            return

        try:
            with open(self.output_mapping, "w", encoding="utf-8") as f:
                f.write("directory,original_filename,new_filename\n")

                for directory, files in sorted(mappings.items()):
                    for old_name, new_name in sorted(files):
                        f.write(f"{directory},{old_name},{new_name}\n")

            logger.info(f"Mapping file written to {self.output_mapping}")

        except Exception as e:
            logger.error(f"Error writing mapping file: {e}")
            self.errors.append(("mapping_file", str(e)))

    def print_summary(self):
        """Print a summary of the operations performed."""
        logger.info("=== Summary ===")

        if self.renamed_files:
            logger.info(f"Renamed files: {len(self.renamed_files)}")
            for old, new in self.renamed_files[:10]:  # Show first 10 examples
                logger.info(f"  {os.path.basename(old)} -> {os.path.basename(new)}")

            if len(self.renamed_files) > 10:
                logger.info(f"  ... and {len(self.renamed_files) - 10} more")

        if self.removed_files:
            logger.info(f"Removed files: {len(self.removed_files)}")
            for file in self.removed_files[:5]:  # Show first 5 examples
                logger.info(f"  {os.path.basename(file)}")

            if len(self.removed_files) > 5:
                logger.info(f"  ... and {len(self.removed_files) - 5} more")

        if self.skipped_files:
            logger.info(f"Skipped files (already normalized): {len(self.skipped_files)}")

        if self.errors:
            logger.info(f"Errors: {len(self.errors)}")
            for file, error in self.errors:
                logger.info(f"  {os.path.basename(file)}: {error}")

def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Normalize filenames in the staging-area directory"
    )
    parser.add_argument(
        "--staging-dir",
        type=str,
        default="/home/locotoki/projects/alfred-agent-platform-v2/docs/staging-area",
        help="Path to the staging-area directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually renaming files",
    )
    parser.add_argument(
        "--no-remove-zone-identifier",
        action="store_false",
        dest="remove_zone_identifier",
        help="Don't remove Zone.Identifier files",
    )
    parser.add_argument(
        "--output-mapping",
        type=str,
        default="filename_mapping.csv",
        help="Path to the output mapping file",
    )
    parser.add_argument(
        "--hex-suffix-pattern",
        type=str,
        default=r"\s+[0-9a-f]{32}",
        help="Regex pattern to match hexadecimal suffixes in filenames",
    )

    args = parser.parse_args()

    # Run the normalization process
    normalizer = FilenameNormalizer(
        staging_dir=args.staging_dir,
        dry_run=args.dry_run,
        remove_zone_identifier=args.remove_zone_identifier,
        hex_suffix_pattern=args.hex_suffix_pattern,
        output_mapping=args.output_mapping,
    )

    stats = normalizer.process_directory()
    normalizer.print_summary()

    # Print overall statistics
    print("\nSummary:")
    print(f"  Files to rename: {stats['renamed']}")
    print(f"  Files to remove: {stats['removed']}")
    print(f"  Files already normalized: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")

    if args.dry_run:
        print("\nThis was a dry run. No files were actually modified.")
        print("To actually rename files, run without the --dry-run option.")
    else:
        print(f"\nMapping file written to: {args.output_mapping}")
        print(f"Successfully normalized filenames in {args.staging_dir}")

if __name__ == "__main__":
    main()
