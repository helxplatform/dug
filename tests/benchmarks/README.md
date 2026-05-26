# Search Quality Benchmarking Framework

A framework for measuring and tracking the quality of Dug's v2.0 search endpoints (`/concepts`, `/variables`, `/studies`, `/cdes`).

## Quick Start

```bash
# 1. Harvest results from the live API and generate curation templates
python -m tests.benchmarks.harvest --generate-expectations

# 2. Curate expectations (use the HTML editor or edit JSON directly)
#    Open tests/benchmarks/curation_editor.html in a browser

# 3. Run benchmarks against curated expectations
python -m pytest tests/benchmarks/ -v -s

# 4. View the report
python -m tests.benchmarks.report
```

## Directory Structure

```
tests/benchmarks/
├── README.md
├── curation_editor.html      # Browser-based UI for grading results
├── conftest.py                # pytest fixtures and test case collection
├── config.py                  # Base URL, paths, defaults
├── client.py                  # HTTP client for v2.0 endpoints
├── metrics.py                 # NDCG, MRR, Precision@k, Recall
├── models.py                  # Pydantic data models
├── harvest.py                 # CLI to fetch results from the live API
├── report.py                  # Console/JSON report generator
├── test_search_quality.py     # pytest parametrized benchmark tests
└── data/
    ├── search_terms.json      # Input search terms for harvesting
    ├── expectations/          # Curated ground truth (one JSON per endpoint)
    │   ├── concepts.json
    │   ├── variables.json
    │   └── studies.json
    └── snapshots/             # Auto-generated snapshots and reports
```

## Workflow

### Step 1: Define Search Terms

Edit `data/search_terms.json` with the queries you want to benchmark:

```json
[
  {
    "query": "blood pressure",
    "endpoints": ["concepts", "variables"]
  },
  {
    "query": "\"chronic pain\"",
    "endpoints": ["concepts"]
  }
]
```

Queries with double quotes (e.g. `"chronic pain"`) are sent as phrase matches to the API.

### Step 2: Harvest Results

Fetch current results from the live API:

```bash
# Basic harvest (saves a snapshot)
python -m tests.benchmarks.harvest

# Harvest and generate editable expectation templates
python -m tests.benchmarks.harvest --generate-expectations

# Custom options
python -m tests.benchmarks.harvest \
  --base-url https://radx-dev.apps.renci.org/search-api \
  --terms data/search_terms.json \
  --output data/snapshots/ \
  --size 20
```

This creates:
- A timestamped snapshot in `data/snapshots/`
- Expectation templates in `data/expectations/` (with `--generate-expectations`)

### Step 3: Curate Expectations

Each result needs a **relevance grade** assigned by a human reviewer.

#### Option A: HTML Editor (recommended)

1. Open `curation_editor.html` in a browser
2. Click **Load JSON** and select an expectations file (e.g. `data/expectations/concepts.json`), or drag-and-drop the file
3. Click **Harvest from API** to fetch fresh results — scores are captured from Elasticsearch automatically
4. Click **Auto-grade (score)** on any card to assign grades based on each result's Elasticsearch score as a % of the top result score:
   - Score ≥ 70% of top → grade **3** (highly relevant)
   - Score ≥ 40% of top → grade **2** (relevant)
   - Score ≥ 15% of top → grade **1** (marginal)
   - Score < 15% of top → grade **0** (irrelevant)
   - Thresholds are configurable per-card; click **Apply to all cards** to grade everything at once
5. Review the auto-grades and adjust any that look wrong — look especially at results near threshold boundaries
6. Check **must appear** for results that must always be returned
7. Check **must NOT** for results that indicate a search quality problem
8. Set **Min NDCG@10** threshold (e.g. 0.5) for pass/fail
9. Click **Save JSON** and replace the file in `data/expectations/` (internal score fields are stripped automatically)

> **Note:** Auto-grade is a starting point, not a substitute for human review. Results near threshold boundaries (e.g., 38%, 68%) should be checked manually. The ES score reflects keyword match quality, not semantic relevance — a result can score high by matching a synonym rather than being truly relevant.

#### Option B: Edit JSON Directly

```json
{
  "query": "blood pressure",
  "endpoint": "concepts",
  "concept_id": null,
  "curated_at": "2026-03-17",
  "expected_results": [
    {"id": "HP:0032263", "name": "Increased blood pressure", "relevance_grade": 3},
    {"id": "MONDO:0005044", "name": "hypertension", "relevance_grade": 3},
    {"id": "UBERON:0018389", "name": "interoceptor", "relevance_grade": 0}
  ],
  "must_appear": ["HP:0032263", "MONDO:0005044"],
  "must_not_appear": [],
  "min_ndcg_at_10": 0.5
}
```

> **Note:** Only test cases with at least one graded result (or `must_appear` entries) are picked up by pytest. Uncurated cases are silently skipped.

### Step 4: Run Benchmarks

```bash
# Run all benchmark tests
python -m pytest tests/benchmarks/ -v -s

# Run only concepts benchmarks
python -m pytest tests/benchmarks/ -v -s -k "concepts"

# Point at a different API
DUG_BENCHMARK_URL=https://other-env.example.com/search-api python -m pytest tests/benchmarks/ -v -s
```

### Step 5: View Reports

```bash
# Print the most recent report
python -m tests.benchmarks.report

# Print a specific report
python -m tests.benchmarks.report data/snapshots/report_20260317_141521.json
```

Example output:

```
==========================================================================================
  Search Quality Benchmark Report
  Run: 2026-03-17T14:15:21  |  API: https://radx-dev.apps.renci.org/search-api
==========================================================================================

Endpoint     Query                      NDCG@5  NDCG@10    MRR    P@5   P@10  Recall  #Res
------------------------------------------------------------------------------------------
concepts     blood pressure              0.984    0.957  1.000  1.000  0.700   1.000    20
concepts     diabetes                    0.806    0.880  1.000  1.000  0.800   1.000    13
concepts     heart failure               0.813    0.804  1.000  1.000  0.600   1.000    20
------------------------------------------------------------------------------------------
AVERAGE                                           0.880  1.000

3 test cases evaluated.
```

## Metrics

| Metric | What It Measures | Range |
|---|---|---|
| **NDCG@k** | Are highly relevant results ranked near the top? | 0–1 (1 = perfect ranking) |
| **MRR** | How quickly does the first relevant result appear? | 0–1 (1 = first result is relevant) |
| **P@k** | What fraction of the top-k results are relevant? | 0–1 |
| **Recall** | Were all `must_appear` items found in the results? | 0–1 |

A result is considered "relevant" for MRR and Precision calculations when its grade is ≥ 2.

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `DUG_BENCHMARK_URL` | `https://radx-dev.apps.renci.org/search-api` | API base URL |

Edit `config.py` to change default result size, k-values, or file paths.

## Dependencies

- `httpx` — HTTP client for API calls
- `pytest` — test runner
- `pydantic` — data models

```bash
pip install httpx pytest pydantic
```

## Tips

- **After changing boost/query logic**: re-run benchmarks to measure impact on NDCG scores
- **Regression detection**: compare snapshot files over time to spot ranking shifts
- **Empty results**: queries like `"novel analgesic"` returning 0 concepts may indicate gaps in the knowledge graph, not search bugs
- **Phrase queries**: wrap in escaped quotes in the JSON (e.g. `"\"chronic pain\""`) to test phrase matching behavior
