"""Generate human-readable benchmark reports from JSON results."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .config import SNAPSHOTS_DIR


def print_report(report_path: Path | str | None = None):
    """Print a formatted console report from a benchmark results JSON file.

    If no path given, uses the most recent report in snapshots/.
    """
    if report_path is None:
        reports = sorted(SNAPSHOTS_DIR.glob("report_*.json"))
        if not reports:
            print("No reports found in", SNAPSHOTS_DIR)
            return
        report_path = reports[-1]

    report_path = Path(report_path)
    with open(report_path) as f:
        report = json.load(f)

    results = report.get("results", [])
    if not results:
        print("No results in report.")
        return

    print(f"\n{'=' * 90}")
    print(f"  Search Quality Benchmark Report")
    print(f"  Run: {report.get('run_at', 'unknown')}  |  API: {report.get('base_url', 'unknown')}")
    print(f"{'=' * 90}\n")

    # Header
    header = f"{'Endpoint':<12} {'Query':<25} {'NDCG@5':>7} {'NDCG@10':>8} {'MRR':>6} {'P@5':>6} {'P@10':>6} {'Recall':>7} {'#Res':>5}"
    print(header)
    print("-" * len(header))

    # Per-case rows
    ndcg10_sum = 0.0
    mrr_sum = 0.0
    issues = []

    for r in results:
        query_display = r["query"][:23]
        if r.get("concept_id"):
            query_display = query_display[:18] + "+" + r["concept_id"][:5]

        row = (
            f"{r['endpoint']:<12} "
            f"{query_display:<25} "
            f"{r['ndcg_at_5']:>7.3f} "
            f"{r['ndcg_at_10']:>8.3f} "
            f"{r['mrr']:>6.3f} "
            f"{r['precision_at_5']:>6.3f} "
            f"{r['precision_at_10']:>6.3f} "
            f"{r['recall']:>7.3f} "
            f"{r['total_results']:>5}"
        )
        print(row)

        ndcg10_sum += r["ndcg_at_10"]
        mrr_sum += r["mrr"]

        if r.get("missing_must_appear"):
            issues.append(f"  MISSING in /{r['endpoint']} for '{r['query']}': {r['missing_must_appear']}")
        if r.get("unexpected_must_not_appear"):
            issues.append(f"  UNEXPECTED in /{r['endpoint']} for '{r['query']}': {r['unexpected_must_not_appear']}")

    n = len(results)
    print("-" * len(header))
    print(f"{'AVERAGE':<12} {'':<25} {'':<7} {ndcg10_sum/n:>8.3f} {mrr_sum/n:>6.3f}")

    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues:
            print(issue)

    print(f"\n{n} test cases evaluated.")
    print(f"Report: {report_path}\n")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print_report(path)


if __name__ == "__main__":
    main()
