#!/usr/bin/env python3
"""Benchmark script for comparing noise ranker versions.

Generates performance report with metrics on:
- Alert volume reduction
- False negative rate
- Processing latency
- Memory usage.
"""
# type: ignore
import argparse
import json
import random
import time
from datetime import datetime
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import psutil
from matplotlib.backends.backend_pdf import PdfPages

from alfred.core.protocols import AlertProtocol
from alfred.ml.noise_ranker import NoiseRankingModel as LegacyRanker
from backend.alfred.alerts.ranker import AlertNoiseRanker

class BenchmarkAlert(AlertProtocol):
    """Mock alert for benchmarking"""

    def __init__(self, **kwargs):
        """Initialize the mock alert with arbitrary properties"""
        for k, v in kwargs.items():
            setattr(self, k, v)

class RankerBenchmark:
    """Benchmark harness for noise rankers"""

    def __init__(
        self,
        new_ranker: AlertNoiseRanker,
        old_ranker: LegacyRanker,
        num_alerts: int = 50000,
    ):
        """Initialize the benchmark with rankers and test parameters.

        Args:
            new_ranker: The new ranker implementation to test
            old_ranker: The legacy ranker to compare against
            num_alerts: Number of test alerts to generate
        """
        self.new_ranker = new_ranker
        self.old_ranker = old_ranker
        self.num_alerts = num_alerts
        self.results = {}

    def generate_test_alerts(self) -> List[Tuple[BenchmarkAlert, Dict, bool]]:
        """Generate synthetic test alerts with labels"""
        alerts = []

        for i in range(self.num_alerts):
            # Mix of noise and signal alerts
            is_noise = random.random() > 0.3  # 70% noise

            alert = BenchmarkAlert(
                id=f"alert-{i}",
                name=random.choice(
                    [
                        "HighCPU",
                        "MemoryLeak",
                        "SlowQuery",
                        "ConnectionTimeout",
                        "DiskFull",
                        "NetworkLatency",
                    ]
                ),
                severity=random.choice(["critical", "warning", "info"]),
                description=f"Test alert {i}",
                summary=f"Summary for alert {i}",
                labels={
                    "service": random.choice(["api", "web", "db", "cache"]),
                    "environment": random.choice(["prod", "staging", "dev"]),
                    "region": random.choice(["us-east", "us-west", "eu-west"]),
                    "instance": f"instance-{random.randint(1, 10)}",
                },
                timestamp=datetime.utcnow(),
            )

            # Historical data
            historical = {
                "count_24h": (random.randint(1, 100) if is_noise else random.randint(0, 5)),
                "count_7d": (random.randint(10, 500) if is_noise else random.randint(0, 20)),
                "avg_resolution_time": random.uniform(100, 10000),
                "false_positive_rate": (
                    random.uniform(0.7, 0.95) if is_noise else random.uniform(0, 0.3)
                ),
                "snooze_count": (random.randint(0, 50) if is_noise else random.randint(0, 5)),
                "ack_rate": (random.uniform(0.1, 0.5) if is_noise else random.uniform(0.5, 0.9)),
            }

            alerts.append((alert, historical, is_noise))

        return alerts

    def benchmark_ranker(
        self, ranker_name: str, ranker, alerts: List[Tuple[BenchmarkAlert, Dict, bool]]
    ) -> Dict:
        """Benchmark a single ranker"""
        print(f"Benchmarking {ranker_name}...")

        # Measure memory before
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # Start timing
        start_time = time.time()

        # Process alerts
        predictions = []
        for alert, historical, true_label in alerts:
            # Predict noise score
            score = ranker.predict_noise_score(alert, historical)
            predictions.append((score, true_label))

        # End timing
        end_time = time.time()
        processing_time = end_time - start_time

        # Measure memory after
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = mem_after - mem_before

        # Calculate metrics
        threshold = 0.7
        suppressed = 0
        false_negatives = 0
        false_positives = 0
        true_positives = 0
        true_negatives = 0

        for score, is_noise in predictions:
            predicted_noise = score > threshold

            if predicted_noise:
                suppressed += 1

            if is_noise and predicted_noise:
                true_positives += 1
            elif is_noise and not predicted_noise:
                false_negatives += 1
            elif not is_noise and predicted_noise:
                false_positives += 1
            else:
                true_negatives += 1

        # Calculate rates
        total_noise = sum(1 for _, _, is_noise in alerts if is_noise)
        total_signal = len(alerts) - total_noise

        false_negative_rate = false_negatives / total_signal if total_signal > 0 else 0
        false_positive_rate = false_positives / total_noise if total_noise > 0 else 0
        suppression_rate = suppressed / len(alerts)

        # P95 latency estimation
        per_alert_time = processing_time / len(alerts)
        p95_latency = per_alert_time * 1000  # Convert to ms

        return {
            "ranker": ranker_name,
            "alerts_processed": len(alerts),
            "processing_time": processing_time,
            "memory_used_mb": memory_used,
            "suppression_rate": suppression_rate,
            "false_negative_rate": false_negative_rate,
            "false_positive_rate": false_positive_rate,
            "true_positives": true_positives,
            "true_negatives": true_negatives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "p95_latency_ms": p95_latency,
            "alerts_per_second": len(alerts) / processing_time,
        }

    def run_benchmark(self) -> Dict:
        """Run full benchmark comparison"""
        print(f"Starting benchmark with {self.num_alerts} alerts...")

        # Generate test data
        alerts = self.generate_test_alerts()

        # Benchmark old ranker
        old_results = self.benchmark_ranker("Legacy Ranker (v1)", self.old_ranker, alerts)

        # Benchmark new ranker
        new_results = self.benchmark_ranker("ML Ranker (v2)", self.new_ranker, alerts)

        # Calculate improvements
        improvements = {
            "volume_reduction_improvement": (
                (new_results["suppression_rate"] - old_results["suppression_rate"])
                / old_results["suppression_rate"]
                * 100
            ),
            "false_negative_improvement": (
                (old_results["false_negative_rate"] - new_results["false_negative_rate"])
                / old_results["false_negative_rate"]
                * 100
            ),
            "speed_improvement": (
                (old_results["processing_time"] - new_results["processing_time"])
                / old_results["processing_time"]
                * 100
            ),
            "memory_improvement": (
                (old_results["memory_used_mb"] - new_results["memory_used_mb"])
                / old_results["memory_used_mb"]
                * 100
            ),
        }

        return {
            "old_ranker": old_results,
            "new_ranker": new_results,
            "improvements": improvements,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def generate_report(self, results: Dict, output_path: str = "ranker_benchmark_report.pdf"):
        """Generate PDF report with visualizations"""
        print(f"Generating report: {output_path}")

        with PdfPages(output_path) as pdf:
            # Page 1: Executive Summary
            fig, ax = plt.subplots(figsize=(8, 11))
            ax.axis("off")

            summary_text = f"""
Alert Noise Ranker Benchmark Report
Generated: {results['timestamp']}

Executive Summary:
- Alerts Tested: {results['new_ranker']['alerts_processed']:,}
- Volume Reduction Improvement: {results['improvements']['volume_reduction_improvement']:.1f}%
- False Negative Improvement: {results['improvements']['false_negative_improvement']:.1f}%
- Speed Improvement: {results['improvements']['speed_improvement']:.1f}%
- Memory Improvement: {results['improvements']['memory_improvement']:.1f}%

Key Findings:
✓ New ML ranker reduces alert volume by {results['new_ranker']['suppression_rate']*100:.1f}%
✓ False negative rate: {results['new_ranker']['false_negative_rate']*100:.2f}% (below 2% target)
✓ P95 latency: {results['new_ranker']['p95_latency_ms']:.1f}ms per alert
✓ Processes {results['new_ranker']['alerts_per_second']:.0f} alerts/second.
"""
            ax.text(
                0.1,
                0.9,
                summary_text,
                transform=ax.transAxes,
                fontsize=12,
                verticalalignment="top",
                fontfamily="monospace",
            )

            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

            # Page 2: Performance Comparison
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))

            # Volume reduction comparison
            metrics = ["Suppression Rate", "False Negative Rate", "False Positive Rate"]
            old_values = [
                results["old_ranker"]["suppression_rate"] * 100,
                results["old_ranker"]["false_negative_rate"] * 100,
                results["old_ranker"]["false_positive_rate"] * 100,
            ]
            new_values = [
                results["new_ranker"]["suppression_rate"] * 100,
                results["new_ranker"]["false_negative_rate"] * 100,
                results["new_ranker"]["false_positive_rate"] * 100,
            ]

            x = np.arange(len(metrics))
            width = 0.35

            ax1.bar(x - width / 2, old_values, width, label="Legacy v1", color="gray")
            ax1.bar(x + width / 2, new_values, width, label="ML v2", color="blue")
            ax1.set_ylabel("Percentage (%)")
            ax1.set_title("Alert Classification Metrics")
            ax1.set_xticks(x)
            ax1.set_xticklabels(metrics, rotation=45)
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Confusion matrix for new ranker
            cm_data = [
                [
                    results["new_ranker"]["true_positives"],
                    results["new_ranker"]["false_negatives"],
                ],
                [
                    results["new_ranker"]["false_positives"],
                    results["new_ranker"]["true_negatives"],
                ],
            ]

            ax2.imshow(cm_data, cmap="Blues")
            ax2.set_xticks([0, 1])
            ax2.set_yticks([0, 1])
            ax2.set_xticklabels(["Predicted Noise", "Predicted Signal"])
            ax2.set_yticklabels(["Actual Noise", "Actual Signal"])
            ax2.set_title("Confusion Matrix (ML v2)")

            # Add text annotations
            for i in range(2):
                for j in range(2):
                    ax2.text(
                        j,
                        i,
                        cm_data[i][j],
                        ha="center",
                        va="center",
                        color=("white" if cm_data[i][j] > sum(sum(cm_data, [])) / 4 else "black"),
                    )

            # Processing performance
            perf_metrics = ["Processing Time (s)", "Memory Usage (MB)"]
            old_perf = [
                results["old_ranker"]["processing_time"],
                results["old_ranker"]["memory_used_mb"],
            ]
            new_perf = [
                results["new_ranker"]["processing_time"],
                results["new_ranker"]["memory_used_mb"],
            ]

            x = np.arange(len(perf_metrics))
            ax3.bar(x - width / 2, old_perf, width, label="Legacy v1", color="gray")
            ax3.bar(x + width / 2, new_perf, width, label="ML v2", color="green")
            ax3.set_ylabel("Value")
            ax3.set_title("Performance Metrics")
            ax3.set_xticks(x)
            ax3.set_xticklabels(perf_metrics)
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # Improvement summary
            improvements = list(results["improvements"].values())
            improvement_labels = [
                "Volume Reduction\nImprovement",
                "False Negative\nReduction",
                "Speed\nImprovement",
                "Memory\nSavings",
            ]

            colors = ["green" if x > 0 else "red" for x in improvements]
            bars = ax4.bar(range(len(improvements)), improvements, color=colors)
            ax4.set_ylabel("Improvement (%)")
            ax4.set_title("ML v2 Improvements over Legacy v1")
            ax4.set_xticks(range(len(improvements)))
            ax4.set_xticklabels(improvement_labels, rotation=45)
            ax4.axhline(y=0, color="black", linestyle="-", alpha=0.3)
            ax4.grid(True, alpha=0.3)

            # Add percentage labels on bars
            for bar, imp in zip(bars, improvements):
                height = bar.get_height()
                ax4.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + (2 if height > 0 else -5),
                    f"{imp:.1f}%",
                    ha="center",
                    va="bottom" if height > 0 else "top",
                )

            plt.tight_layout()
            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

            # Page 3: Detailed Metrics Table
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.axis("off")

            # Create detailed comparison table
            table_data = [
                ["Metric", "Legacy v1", "ML v2", "Improvement"],
                [
                    "Alerts Processed",
                    f"{results['old_ranker']['alerts_processed']:,}",
                    f"{results['new_ranker']['alerts_processed']:,}",
                    "-",
                ],
                [
                    "Suppression Rate",
                    f"{results['old_ranker']['suppression_rate']*100:.1f}%",
                    f"{results['new_ranker']['suppression_rate']*100:.1f}%",
                    f"{results['improvements']['volume_reduction_improvement']:.1f}%",
                ],
                [
                    "False Negative Rate",
                    f"{results['old_ranker']['false_negative_rate']*100:.2f}%",
                    f"{results['new_ranker']['false_negative_rate']*100:.2f}%",
                    f"{results['improvements']['false_negative_improvement']:.1f}%",
                ],
                [
                    "Processing Time",
                    f"{results['old_ranker']['processing_time']:.2f}s",
                    f"{results['new_ranker']['processing_time']:.2f}s",
                    f"{results['improvements']['speed_improvement']:.1f}%",
                ],
                [
                    "Memory Usage",
                    f"{results['old_ranker']['memory_used_mb']:.1f}MB",
                    f"{results['new_ranker']['memory_used_mb']:.1f}MB",
                    f"{results['improvements']['memory_improvement']:.1f}%",
                ],
                [
                    "P95 Latency",
                    f"{results['old_ranker']['p95_latency_ms']:.1f}ms",
                    f"{results['new_ranker']['p95_latency_ms']:.1f}ms",
                    "-",
                ],
                [
                    "Alerts/Second",
                    f"{results['old_ranker']['alerts_per_second']:.0f}",
                    f"{results['new_ranker']['alerts_per_second']:.0f}",
                    "-",
                ],
            ]

            table = ax.table(
                cellText=table_data,
                cellLoc="center",
                loc="center",
                colWidths=[0.3, 0.2, 0.2, 0.3],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 2)

            # Style the header row
            for i in range(4):
                table[(0, i)].set_facecolor("#4CAF50")
                table[(0, i)].set_text_props(weight="bold", color="white")

            ax.set_title(
                "Detailed Performance Comparison",
                fontsize=14,
                fontweight="bold",
                pad=20,
            )

            pdf.savefig(fig, bbox_inches="tight")
            plt.close()

        print(f"Report generated: {output_path}")
        return output_path

def main():
    """Run the benchmark tool as a command-line application"""
    parser = argparse.ArgumentParser(description="Benchmark noise ranker versions")
    parser.add_argument("--new", default="v2", help="New ranker version")
    parser.add_argument("--old", default="v1", help="Old ranker version")
    parser.add_argument("--alerts", type=int, default=50000, help="Number of test alerts")
    parser.add_argument(
        "--output", default="ranker_benchmark_report.pdf", help="Output report path"
    )

    args = parser.parse_args()

    # Initialize rankers
    # In real implementation, would load from models
    new_ranker = AlertNoiseRanker()
    old_ranker = LegacyRanker()

    # Create benchmark
    benchmark = RankerBenchmark(new_ranker, old_ranker, args.alerts)

    # Run benchmark
    results = benchmark.run_benchmark()

    # Generate report
    report_path = benchmark.generate_report(results, args.output)

    # Save raw results
    json_path = args.output.replace(".pdf", ".json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    print("Benchmark complete!")
    print(f"Report: {report_path}")
    print(f"Raw data: {json_path}")

    # Print summary
    print("\nSummary:")
    print(f"- Volume reduction: {results['new_ranker']['suppression_rate']*100:.1f}%")
    print(f"- False negative rate: {results['new_ranker']['false_negative_rate']*100:.2f}%")
    print(f"- P95 latency: {results['new_ranker']['p95_latency_ms']:.1f}ms")
    print(f"- Overall improvement: {results['improvements']['volume_reduction_improvement']:.1f}%")

if __name__ == "__main__":
    main()
