# \!/usr/bin/env python3
"""CLI tool for flake detection analysis."""
import argparse
import json
import sys

from . import analyze, emit_github_summary

def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Analyze pytest JSON report for flaky tests")
    parser.add_argument("json_report", help="Path to pytest JSON report file")
    parser.add_argument("--emit-summary", action="store_true", help="Emit GitHub Actions summary")
    parser.add_argument("--output", help="Output file for analysis results (JSON)")

    args = parser.parse_args()

    # Analyze the report
    result = analyze(args.json_report)

    # Print results
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return 1

    print("📊 Analysis Results:")
    print(f"   Total tests: {result.get('total_tests', 0)}")
    print(f"   Failed tests: {result.get('failed_tests', 0)}")
    print(f"   Flaky tests: {len(result.get('flakes', []))}")

    if result.get("flakes"):
        print("\n⚠️  Flaky tests detected:")
        for i, flake in enumerate(result["flakes"][:5], 1):
            print(f"   {i}. {flake}")
        if len(result["flakes"]) > 5:
            print(f"   ... and {len(result['flakes']) - 5} more")
    else:
        print("\n✅ No flaky tests detected\!")

    # Emit GitHub summary if requested
    if args.emit_summary:
        emit_github_summary(result)

    # Save to output file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(f"📁 Results saved to {args.output}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
