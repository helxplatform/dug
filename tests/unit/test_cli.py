from unittest.mock import patch

from pytest import mark

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
@patch('dug.cli.crawl')
def test_dug_cli_main_crawl(mock_crawl):
    main(["crawl", "somefile.csv", "--parser", "topmedtag"])
    assert mock_crawl.called_once()

@mark.cli
@patch('dug.cli.crawl')
def test_dug_cli_main_extract_dug_elements(mock_crawl):
    main(["crawl", "somefile.csv", "--parser", "topmedtag", "-x"])
    assert mock_crawl.called_once()
    assert mock_crawl.call_args_list[0].args[0].extract_dug_elements

@mark.cli
@patch('dug.cli.crawl')
def test_dug_cli_main_extract_dug_elements_none(mock_crawl):
    main(["crawl", "somefile.csv", "--parser", "topmedtag"])
    assert mock_crawl.called_once()
    assert not mock_crawl.call_args_list[0].args[0].extract_dug_elements

@mark.cli
@patch('dug.cli.search')
def test_dug_cli_main_search(mock_search):
    # mock_search.search.return_value = "Searching!"
    main(["search", "-q", "heart attack", "-t", "variables", "-k", "namespace=default"])
    assert mock_search.called_once()
