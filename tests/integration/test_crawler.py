import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from helx.search.core.crawler import Crawler
from tests.integration.conftest import TEST_DATA_DIR


def test_crawler_init():
    crawl_file = TEST_DATA_DIR / "crawler_sample_file.csv"
    parser = MagicMock()
    annotator = MagicMock()
    tranqlizer = MagicMock()
    tranql_queries = MagicMock()
    http_session = MagicMock()

    crawler = Crawler(
        crawl_file=crawl_file,
        parser=parser,
        annotator=annotator,
        tranqlizer=tranqlizer,
        tranql_queries=tranql_queries,
        http_session=http_session,
    )

    assert crawler.crawlspace == "crawl"
    assert len(crawler.elements) == 0
    assert len(crawler.concepts) == 0


def test_make_crawlspace():
    crawl_file = TEST_DATA_DIR / "crawler_sample_file.csv"
    parser = MagicMock()
    annotator = MagicMock()
    tranqlizer = MagicMock()
    tranql_queries = MagicMock()
    http_session = MagicMock()

    crawler = Crawler(
        crawl_file=crawl_file,
        parser=parser,
        annotator=annotator,
        tranqlizer=tranqlizer,
        tranql_queries=tranql_queries,
        http_session=http_session,
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        crawler.crawlspace = str(Path(temp_dir) / 'crawl')
        assert not Path(crawler.crawlspace).exists()
        crawler.make_crawlspace()
        assert Path(crawler.crawlspace).exists()


def test_crawl():
    crawl_file = TEST_DATA_DIR / "crawler_sample_file.csv"
    parser = MagicMock()
    annotator = MagicMock()
    tranqlizer = MagicMock()
    tranql_queries = MagicMock()
    http_session = MagicMock()

    crawler = Crawler(
        crawl_file=crawl_file,
        parser=parser,
        annotator=annotator,
        tranqlizer=tranqlizer,
        tranql_queries=tranql_queries,
        http_session=http_session,
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        crawler.crawlspace = str(Path(temp_dir) / 'crawl')
        crawler.crawl()
