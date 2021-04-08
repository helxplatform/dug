#!/usr/bin/env python3
"""
Represents the entrypoint for command line tools.
"""

import argparse
import os

from dug.core import Dug, logger


def get_argparser():

    parser = argparse.ArgumentParser(description='DUG-Search Crawler')
    parser.set_defaults(func=lambda _args: parser.print_usage())

    subparsers = parser.add_subparsers(help="Help for subparser")

    # Crawl subcommand
    crawl_parser = subparsers.add_parser('crawl', help='crawl help')
    crawl_parser.set_defaults(func=crawl)
    crawl_parser.add_argument(
        'target',
        type=str,
        help='Input file containing things you want to crawl/index',
    )

    crawl_parser.add_argument(
        '--parser',
        help='Parser to use for parsing elements from crawl file',
        dest="parser_type",
        required=True
    )

    crawl_parser.add_argument(
        '--element-type',
        help='[Optional] Coerce all elements to a certain data type (e.g. DbGaP Variable).\n'
             'Determines what tab elements will appear under in Dug front-end',
        dest="element_type",
        default=None
    )

    # Status subcommand
    status_parser = subparsers.add_parser('status', help='crawl help')
    status_parser.set_defaults(func=status)

    # Search subcommand
    search_parser = subparsers.add_parser('search', help='crawl help')
    search_parser.set_defaults(func=search)

    search_parser.add_argument(
        '-q', '--query',
        # nargs='+',
        help='Query to search for',
    )
    search_parser.add_argument(
        '-i', '--index',
        help = 'Index to search in',
    )
    return parser


def crawl(args):
    dug = Dug()
    dug.crawl(args.target, args.parser_type, args.element_type)


def search(args):
    dug = Dug()
    index = args.index
    query = args.query
    response = dug.search(index, query)
    # TODO add parsing options

    print(response)


def status(args):
    print("Status is ... OK!")


def main():
    log_level = os.getenv("DUG_LOG_LEVEL", "INFO")

    logger.setLevel(log_level)

    arg_parser = get_argparser()

    args = arg_parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
