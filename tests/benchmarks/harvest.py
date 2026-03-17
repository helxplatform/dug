"""CLI tool to harvest search results from the live API and generate curation templates.

Usage:
    python -m tests.benchmarks.harvest [OPTIONS]

Options:
    --base-url URL    API base URL (default: from config / DUG_BENCHMARK_URL env)
    --terms PATH      Path to search_terms.json (default: data/search_terms.json)
    --output PATH     Output directory for snapshots (default: data/snapshots/)
    --generate-expectations   Also generate expectation templates for curation
    --size N          Number of results to fetch per query (default: 20)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from .client import DugSearchClient
from .config import BASE_URL, DEFAULT_SIZE, EXPECTATIONS_DIR, SEARCH_TERMS_PATH, SNAPSHOTS_DIR
from .models import SearchTerm


def harvest(
    base_url: str = BASE_URL,
    terms_path: Path = SEARCH_TERMS_PATH,
    output_dir: Path = SNAPSHOTS_DIR,
    generate_expectations: bool = False,
    size: int = DEFAULT_SIZE,
) -> dict:
    """Run all search terms against the live API and save results.

    Returns a summary dict with counts.
    """
    terms_path = Path(terms_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(terms_path) as f:
        raw_terms = json.load(f)

    terms = [SearchTerm(**t) for t in raw_terms]
    client = DugSearchClient(base_url=base_url)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot = {
        "harvested_at": timestamp,
        "base_url": base_url,
        "results": []
    }

    # Group expectations by endpoint for template generation
    expectation_templates: dict[str, list] = {}

    total_queries = 0
    for term in terms:
        for endpoint in term.endpoints:
            print(f"  Querying /{endpoint} for '{term.query}'"
                  f"{' (concept=' + term.concept_id + ')' if term.concept_id else ''}...")

            try:
                results = client.search(
                    endpoint=endpoint,
                    query=term.query,
                    concept_id=term.concept_id,
                    size=size,
                )
            except Exception as e:
                print(f"    ERROR: {e}")
                results = []

            entry = {
                "query": term.query,
                "endpoint": endpoint,
                "concept_id": term.concept_id,
                "result_count": len(results),
                "results": [r.model_dump() for r in results],
            }
            snapshot["results"].append(entry)
            total_queries += 1

            # Build expectation template
            if generate_expectations:
                expectation_entry = {
                    "query": term.query,
                    "endpoint": endpoint,
                    "concept_id": term.concept_id,
                    "curated_at": None,
                    "expected_results": [
                        {
                            "id": r.id,
                            "name": r.name,
                            "relevance_grade": None,
                        }
                        for r in results
                    ],
                    "must_appear": [],
                    "must_not_appear": [],
                    "min_ndcg_at_10": 0.0,
                }
                expectation_templates.setdefault(endpoint, []).append(expectation_entry)

            print(f"    -> {len(results)} results (top: {results[0].name if results else 'none'})")

    # Save snapshot
    snapshot_path = output_dir / f"snapshot_{timestamp}.json"
    with open(snapshot_path, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"\nSnapshot saved to {snapshot_path}")

    # Save expectation templates
    if generate_expectations:
        expectations_dir = Path(EXPECTATIONS_DIR)
        expectations_dir.mkdir(parents=True, exist_ok=True)
        for endpoint, entries in expectation_templates.items():
            template_path = expectations_dir / f"{endpoint}.json"
            if template_path.exists():
                print(f"  Expectations file already exists: {template_path} (skipping)")
                continue
            with open(template_path, "w") as f:
                json.dump(entries, f, indent=2, default=str)
            print(f"  Expectation template saved to {template_path}")
        print("\nReview the templates in data/expectations/ and fill in relevance_grade values (0-3).")

    return {"total_queries": total_queries, "snapshot_path": str(snapshot_path)}


def main():
    parser = argparse.ArgumentParser(description="Harvest search results from the live Dug API")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    parser.add_argument("--terms", default=str(SEARCH_TERMS_PATH), help="Path to search_terms.json")
    parser.add_argument("--output", default=str(SNAPSHOTS_DIR), help="Output directory for snapshots")
    parser.add_argument("--generate-expectations", action="store_true",
                        help="Generate expectation templates for curation")
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Results per query")
    args = parser.parse_args()

    print(f"Harvesting from {args.base_url}...")
    result = harvest(
        base_url=args.base_url,
        terms_path=Path(args.terms),
        output_dir=Path(args.output),
        generate_expectations=args.generate_expectations,
        size=args.size,
    )
    print(f"\nDone. {result['total_queries']} queries executed.")


if __name__ == "__main__":
    main()
