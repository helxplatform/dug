#!/usr/bin/env python3
"""
Represents the entrypoint for command line tools.
"""

import argparse
import os

from dug.core import Dug, logger


def get_argparser():

    argument_parser = argparse.ArgumentParser(description='Dug: Semantic Search')
    argument_parser.set_defaults(func=lambda _args: argument_parser.print_usage())

    subparsers = argument_parser.add_subparsers(
        title="Commands",
    )

    # Crawl subcommand
    crawl_parser = subparsers.add_parser('crawl', help='Crawl and index some input')
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

    # Search subcommand
    search_parser = subparsers.add_parser('search', help='Apply semantic search')
    search_parser.set_defaults(func=search)

    search_parser.add_argument(
        '-q', '--query',
        # nargs='+',
        help='Query to search for',
    )
    search_parser.add_argument(
        '-i', '--index',
        help='Index to search in',
    )

    search_parser.add_argument(
        '-t', '--target',
        help="Target (one of 'variables' or 'concepts')",
    )

    search_parser.add_argument(
        '-c', '--concept',
        default=None,
        help="Concept to filter by when searching variables"
    )
    # Status subcommand
    status_parser = subparsers.add_parser('status', help='Check status of dug server')
    status_parser.set_defaults(func=status)

    return argument_parser


def crawl(args):
    dug = Dug()
    dug.crawl(args.target, args.parser_type, args.element_type)


def search(args):
    dug = Dug()
    index = args.index
    query = args.query
    target = args.target
    concept = args.concept
    response = dug.search(index, query, target, concept=concept)

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
