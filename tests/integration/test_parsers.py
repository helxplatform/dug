import pytest

from dug.parsers import DbGaPParser
from tests.integration.conftest import TEST_DATA_DIR


@pytest.mark.skip("Finish this test")
def test_db_gap_parser():
    parser = DbGaPParser()

    parse_file = TEST_DATA_DIR / "dbgap_sample_file.csv"
    parser.parse(parse_file)


@pytest.mark.skip("Finish this test")
def test_topmed_tag_parser():
    pass

