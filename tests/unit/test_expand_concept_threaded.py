"""expand_concept must give the same answer threaded as serial.

The threaded path fetches out of order, so the risk is that kg_answers ends
up depending on which request returned first, or that two threads mutate the
concept at once. Both are covered here: a fetcher with deliberately inverted
latency, and a concept whose add_kg_answer records call order.
"""
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from dug.core.crawler import Crawler


class FakeQueryFactory:
    """Accepts only curies starting with its prefix, like QueryFactory."""

    def __init__(self, prefix):
        self.prefix = prefix

    def is_valid_curie(self, curie):
        return curie.startswith(self.prefix)

    def get_query(self, curie):
        return f"query({curie})"


class FakeAnswer:
    def __init__(self, tag):
        self.tag = tag
        self.nodes = {tag: {}}

    def __eq__(self, other):
        return isinstance(other, FakeAnswer) and other.tag == self.tag

    def __repr__(self):
        return f"FakeAnswer({self.tag})"


class FakeConcept:
    def __init__(self, identifiers):
        self.identifiers = {i: object() for i in identifiers}
        self.kg_answers = {}
        self.applied = []

    def add_kg_answer(self, answer, query_name):
        answer_id = f'{"_".join(answer.nodes.keys())}_{query_name}'
        self.applied.append(answer_id)
        if answer_id not in self.kg_answers:
            self.kg_answers[answer_id] = answer


class InvertedLatencyTranqlizer:
    """Later jobs return first, so ordering bugs surface deterministically."""

    def __init__(self, total, delay=0.02):
        self.total = total
        self.delay = delay
        self.calls = []
        self._n = 0

    def expand_identifier(self, identifier, query_factory, kg_outfile=None):
        n = self._n
        self._n += 1
        time.sleep(self.delay * (self.total - n))
        self.calls.append((identifier, kg_outfile))
        return [FakeAnswer(f"{identifier}:{n}")]


def build_crawler(workers, tranqlizer):
    return Crawler(
        crawl_file="",
        parser=None,
        annotator=None,
        tranqlizer=tranqlizer,
        tranql_queries={
            "disease": FakeQueryFactory("MONDO"),
            "pheno": FakeQueryFactory("HP"),
            "chem": FakeQueryFactory("CHEBI"),
        },
        http_session=None,
        crawl_workers=workers,
    )


IDENTIFIERS = ["MONDO:1", "HP:2", "CHEBI:3", "MONDO:4", "HP:5"]


def test_threaded_matches_serial():
    serial_concept = FakeConcept(IDENTIFIERS)
    build_crawler(1, InvertedLatencyTranqlizer(5)).expand_concept(
        serial_concept)

    threaded_concept = FakeConcept(IDENTIFIERS)
    build_crawler(4, InvertedLatencyTranqlizer(5)).expand_concept(
        threaded_concept)

    # identical keys AND identical apply order, despite inverted latency
    assert threaded_concept.applied == serial_concept.applied
    assert list(threaded_concept.kg_answers) == list(
        serial_concept.kg_answers)


def test_only_valid_curies_are_queried():
    """One query class per prefix, so each identifier yields exactly one."""
    tranqlizer = InvertedLatencyTranqlizer(5, delay=0)
    build_crawler(4, tranqlizer).expand_concept(FakeConcept(IDENTIFIERS))
    assert len(tranqlizer.calls) == len(IDENTIFIERS)
    assert {c[0] for c in tranqlizer.calls} == set(IDENTIFIERS)


def test_excluded_identifiers_are_skipped():
    tranqlizer = InvertedLatencyTranqlizer(5, delay=0)
    crawler = build_crawler(4, tranqlizer)
    crawler.exclude_identifiers = ["MONDO:1", "HP:2"]
    crawler.expand_concept(FakeConcept(IDENTIFIERS))
    assert {c[0] for c in tranqlizer.calls} == {"CHEBI:3", "MONDO:4", "HP:5"}


def test_no_valid_jobs_makes_no_calls():
    tranqlizer = InvertedLatencyTranqlizer(1, delay=0)
    build_crawler(4, tranqlizer).expand_concept(FakeConcept(["UMLS:9"]))
    assert tranqlizer.calls == []


def test_fetch_failure_propagates():
    """A dead TranQL must fail the task, not silently drop the concept."""

    class Boom:
        def expand_identifier(self, *a, **k):
            raise RuntimeError("tranql down")

    with pytest.raises(RuntimeError, match="tranql down"):
        build_crawler(4, Boom()).expand_concept(FakeConcept(IDENTIFIERS))
