#!/usr/bin/env python
#
# export_ddm_as_json_schema.py - Export Dug Data Model as JSON Schema
#
# SYNOPSIS
#   python bin/export_ddm_as_json_schema.py
#

import click
import json
import logging

from dug.core.parsers._base import DugStudy, DugSection, DugVariable

logging.basicConfig(level=logging.INFO)

@click.command()
def export_ddm_as_json_schema():
    """

    :return:
    """
    logging.info("Exporting Dug Data Model as JSON Schema")

    json_schema = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
            # This is what Pydantic supports: https://docs.pydantic.dev/latest/api/json_schema/#pydantic.json_schema.GenerateJsonSchema
        'definitions': {
            'DugSection': DugSection.model_json_schema(),
            'DugVariable': DugVariable.model_json_schema(),
            'DugStudy': DugStudy.model_json_schema()
        },
        # We want to validate a list of heterogenous objects: each item in the list may be any of the Dug objects above.
        'type': 'list',
        'items': {
            'oneOf': [
                {'$ref': '#/definitions/DugSection'},
                {'$ref': '#/definitions/DugVariable'},
                {'$ref': '#/definitions/DugStudy'}
            ]
        }
    }

    print(json.dumps(json_schema, indent=2))


if __name__ == '__main__':
    export_ddm_as_json_schema()
