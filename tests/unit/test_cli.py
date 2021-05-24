from pytest import mark

from unittest.mock import patch

from dug.cli import main, get_argparser


@mark.cli
def test_dug_cli_parser():
    parser = get_argparser()
    parsed_log_level = parser.parse_args(["-l", "DEBUG"])
    parsed_crawl = parser.parse_args(["crawl", "somefile.csv", "--parser", "topmedtag"])
    parsed_search = parser.parse_args(["search", "-q", "heart attack", "-t", "variables", "-k", "namespace=default"])

    assert parsed_log_level.log_level == "DEBUG"

    assert parsed_crawl.target == "somefile.csv"
    assert parsed_crawl.parser_type == "topmedtag"

    assert parsed_search.target == "variables"
    assert parsed_search.query == "heart attack"


@mark.cli
@patch('dug.cli.Dug')
def test_dug_cli_main_crawl(mock_dug):
    mock_dug.search = "Crawling!"
    main(["crawl", "somefile.csv", "--parser", "topmedtag"])


@mark.cli
@patch('dug.cli.Dug')
def test_dug_cli_main_search(mock_dug):
    mock_dug.search.return_value = "Searching!"
    main(["search", "-q", "heart attack", "-t", "variables", "-k", "namespace=default"])
