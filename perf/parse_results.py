"""Parse Locust results and extract p95 latency metrics."""

import csv
import sys

def extract_p95(csv_path):
    """Extract p95 latency from Locust results CSV and validate threshold."""
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
        for row in rows:
            if row["Name"] == "query_rag":
                print("# HELP rag_p95_latency_ms p95 latency in ms")
                print("# TYPE rag_p95_latency_ms gauge")
                print(f'rag_p95_latency_ms {row["95%"]}')
                if float(row["95%"]) > 300:
                    print("ERROR: p95 latency exceeds 300ms", file=sys.stderr)
                    exit(1)

if __name__ == "__main__":
    extract_p95(sys.argv[1])  # type: ignore
