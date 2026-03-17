"""Configuration for the benchmarking framework."""
from __future__ import annotations

import os
from pathlib import Path

BENCHMARKS_DIR = Path(__file__).parent
DATA_DIR = BENCHMARKS_DIR / "data"
EXPECTATIONS_DIR = DATA_DIR / "expectations"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
SEARCH_TERMS_PATH = DATA_DIR / "search_terms.json"

BASE_URL = os.environ.get("DUG_BENCHMARK_URL", "https://radx-dev.apps.renci.org/search-api")

ENDPOINTS = ["concepts", "variables", "studies", "cdes"]

DEFAULT_SIZE = 20
DEFAULT_K_VALUES = [5, 10]
