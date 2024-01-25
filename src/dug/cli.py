#!/usr/bin/env python3
"""
Represents the entrypoint for command line tools.
"""

import argparse
import os
import json

from dug.config import Config
from dug.core import Dug, logger, DugFactory


class KwargParser(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        for value in values:
            key, value = value.split('=', maxsplit=1)
            getattr(namespace, self.dest)[key] = value


def get_argparser():
    argument_parser = argparse.ArgumentParser(description='Dug: Semantic Search')
    argument_parser.set_defaults(func=lambda _args: argument_parser.print_usage())
    argument_parser.add_argument(
        '-l', '--level',
        type=str,
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        dest='log_level',
        default=os.getenv("DUG_LOG_LEVEL", "INFO"),
        help="Log level"
    )

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
        '-p', '--parser',
        help='Parser to use for parsing elements from crawl file',
        dest="parser_type",
        required=True
    )

    crawl_parser.add_argument(
        '-a', '--annotator',
        help='Annotator used to annotate identifiers in crawl file',
        dest="annotator_type",
        default="monarch"
    )

    crawl_parser.add_argument(
        '-e', '--element-type',
        help='[Optional] Coerce all elements to a certain data type (e.g. DbGaP Variable).\n'
             'Determines what tab elements will appear under in Dug front-end',
        dest="element_type",
        default=None
    )

    crawl_parser.add_argument(
        "-x", "--extract-from-graph",
        help="[Optional] Extract dug elements for tranql using concepts from annotation",
        dest="extract_dug_elements",
        default=False,
        action="store_true"
    )

    # Search subcommand
    search_parser = subparsers.add_parser('search', help='Apply semantic search')
    search_parser.set_defaults(func=search)

    search_parser.add_argument(
        '-t', '--target',
        dest='target',
        help="Defines which search strategy to use (e.g. variables, concepts, kg, etc.)",
    )

    search_parser.add_argument(
        '-q', '--query',
        dest='query',
        help='Query to search for',
    )

    search_parser.add_argument(
        '-k',
        '--kwargs',
        nargs='*',
        dest='kwargs',
        default={},
        action=KwargParser,
        help="Optional keyword arguments that will be passed into the search target",
    )

    # Status subcommand
    # TODO implement this
    # status_parser = subparsers.add_parser('status', help='Check status of dug server')
    # status_parser.set_defaults(func=status)

    return argument_parser


def crawl(args):
    config = Config.from_env()
    if not args.extract_dug_elements:
        # disable extraction
        config.node_to_element_queries = {}
    factory = DugFactory(config)
    dug = Dug(factory)
    dug.crawl(args.target, args.parser_type, args.annotator_type, args.element_type)


def search(args):
    config = Config.from_env()
    factory = DugFactory(config)
    dug = Dug(factory)
    # dug = Dug()
    response = dug.search(args.target, args.query, **args.kwargs)
    # Using json.dumps raises 'TypeError: Object of type ObjectApiResponse is not JSON serializable'
    #jsonResponse = json.dumps(response, indent = 2)
    print(response)

def datatypes(args):
    config = Config.from_env()
    factory = DugFactory(config)
    dug = Dug(factory)
    # dug = Dug()
    response = dug.info(args.target, **args.kwargs)


def status(args):
    print("Status check is not implemented yet!")


def main(args=None):

    arg_parser = get_argparser()

    args = arg_parser.parse_args(args)

    try:
        logger.setLevel(args.log_level)
    except ValueError:
        print(f"Log level must be one of CRITICAL, ERROR, WARNING, INFO, DEBUG. You entered {args.log_level}")

    args.func(args)


if __name__ == '__main__':
    main()
