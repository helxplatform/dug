# AGENTS.md

This file provides guidance to software agents like Claude Code (claude.ai/code) when working with code in this repository.

## What is Dug

Dug applies semantic web and knowledge graph methods to make research data more findable. It ingests biomedical metadata (e.g. dbGaP study variables), annotates them with ontological terms (via Monarch/SciGraph NLP), normalizes identifiers (via Translator SRI), expands concept graphs (via TranQL), and indexes everything into Elasticsearch for full-text search.

## Setup

```bash
make init        # enable git commit-msg hook (run once after clone)
make install     # pip install requirements.txt
```

The package sources live under `src/` and PYTHONPATH must include `src/`. The Makefile sets this automatically. If running commands outside make, set:
```bash
export PYTHONPATH=$(pwd)/src
```

Version is single-sourced at `src/dug/_version.py`.

## Testing

```bash
make test                                          # unit tests with coverage
pytest tests/unit                                  # unit tests only
pytest tests/integration                           # integration tests (requires live services)
pytest tests/unit/test_parsers.py                  # single test file
pytest tests/unit/test_parsers.py::TestClassName   # single test class
```

Integration tests require live Elasticsearch and Redis (see docker-compose). Unit tests run without external services.

## Running the stack

```bash
docker-compose up   # starts Elasticsearch, Redis, Neo4J, and Dug search API
```

When connecting to docker services from the host shell, override hosts:
```bash
source .env && export $(cut -d= -f1 .env)
export ELASTIC_API_HOST=localhost
export REDIS_HOST=localhost
```

## CLI usage

```bash
# Crawl (annotate + index) a dataset
dug crawl <file_or_url> -p <parser_type> [-a <annotator>] [-e <element_type>]

# Search
dug search -q "vein" -t concepts
dug search -q "vein" -t variables -k "concept=UBERON:0001638"
```

## Architecture

### Pipeline: crawl → index → search

1. **Parser** (`src/dug/core/parsers/`) — converts raw files (dbGaP XML, CSV, etc.) into `DugElement` and `DugConcept` objects. Parsers are registered via the pluggy hook `define_parsers` in `src/dug/core/parsers/__init__.py`.

2. **Annotator** (`src/dug/core/annotators/`) — takes element descriptions and calls external NLP services (Monarch or SapBERT) to extract `DugIdentifier` (ontology CURIEs). Registered via `define_annotators` hookspec in `src/dug/hookspecs.py`.

3. **Concept Expander / TranQL** (`src/dug/core/concept_expander.py`, `src/dug/core/tranql.py`) — takes identified CURIEs and expands them via TranQL queries to build knowledge graph answers. Results cached in Redis.

4. **Crawler** (`src/dug/core/crawler.py`) — orchestrates parsing → annotation → TranQL expansion for a single file.

5. **Indexer** (`src/dug/core/index.py`) — writes `DugElement`, `DugConcept`, and KG answers into Elasticsearch indices (`concepts_index`, `variables_index`, `kg_index`).

6. **Search API** (`src/dug/server.py`) — FastAPI app exposing `/search`, `/search_var`, `/search_var_grouped`, `/search_kg`, `/search_study`, `/search_program`, and `/program_list` endpoints. Started via uvicorn on port 8181 (default).

### Key types

- `DugElement` (`src/dug/core/parsers/_base.py`) — a single searchable item (e.g. one dbGaP variable).
- `DugConcept` (`src/dug/core/parsers/_base.py`) — an ontology concept that groups elements; holds `DugIdentifier`s and `kg_answers`.
- `DugIdentifier` (`src/dug/core/annotators/_base.py`) — an ontology CURIE with labels, synonyms, and types.

### Plugin system

Dug uses **pluggy** to allow external packages to register new parsers and annotators via setuptools entrypoints (`dug` group). The built-in parsers and annotators are loaded as plugins in `src/dug/core/__init__.py:get_plugin_manager()`.

To add a new parser: implement `Parser = Callable[[Any], Iterable[Indexable]]` and register it in a `define_parsers` hookimpl. Currently supported parsers include `dbgap`, `topmedcsv`, `topmedtag`, `anvil`, `crdc`, `kfdrc`, `sprint`, `bacpac`, `heal-studies`, `heal-research`, `ctn`, `radx`, and others (see `src/dug/core/parsers/__init__.py`).

### Configuration

`src/dug/config.py` defines the `Config` dataclass. All values have defaults and can be overridden via environment variables read in `Config.from_env()`. Key env vars: `ELASTIC_API_HOST`, `ELASTIC_PASSWORD`, `REDIS_HOST`, `REDIS_PASSWORD`. See `.env.template` for the full list.

## Commit convention

This repo uses [Conventional Commits](https://www.conventionalcommits.org/) enforced by the `.githooks/commit-msg` hook. Run `make init` to activate it.
