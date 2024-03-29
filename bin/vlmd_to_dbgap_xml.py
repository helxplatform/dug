#
# Script to convert HEAL VLMD formatted files into dbGaP XML files for import into Dug.
#
# USAGE:
#   python bin/vlmd_to_dbgap_xml.py input.csv --output output.xml
#
# This currently only supports HEAL VLMD CSV format files (with a focus on supporting the files produced
# by the vlmd tool, see https://github.com/norc-heal/healdata-utils), but we hope to extend this to
# support HEAL VLMD JSON files as well. See format documentation at https://github.com/HEAL/heal-metadata-schemas
#
import csv
import json
import logging
import os
import re
import sys
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ETree
from collections import defaultdict
from datetime import datetime

import click

# Some defaults.
HDP_ID_PREFIX = 'HEALDATAPLATFORM:'

# Turn on logging
logging.basicConfig(level=logging.INFO)


# Set up command line arguments.
@click.command()
@click.argument('input_file', type=click.Path(exists=True), required=True)
@click.option('--file-format', '--format',
              type=click.Choice(['CSV'], case_sensitive=False), default='CSV',
              help="The file format to convert from (CSV in the VLMD format is the default, and the only one "
                   "currently supported)")
@click.option('--output', '-o', type=click.File(mode='w'), default=sys.stdout,
              help="Where the output dbGaP XML file is written. Defaults to STDOUT.")
@click.option('--study-id', type=str, help="The HEAL Data Platform study ID of this study. Should start with 'HDP'.")
@click.option('--appl-id', type=str, help="The NIH APPLication ID of this study. Usually a numerical identifier.")
@click.option('--study-name', type=str, help="The name or title of this study.")
def vlmd_to_dbgap_xml(input_file, output, file_format, study_id, appl_id, study_name):
    """
    Convert a VLMD file (INPUT_FILE) into a dbGaP XML file for ingest into Dug.
    \f
    # \f truncates the help text as per https://click.palletsprojects.com/en/8.1.x/documentation/#truncating-help-texts

    :param input_file: The VLMD file to read.
    :param output: Where the dbGaP XML file should be written.
    :param file_format: The file format to read. Only [HEAL VLMD] 'CSV' is currently supported.
    :param study_id: The HEAL Data Platform Study ID to use in Dug (without a prefix).
    :param appl_id: The APPL ID to use in Dug.
    :param study_name: The study name ot use.
    """

    assert file_format == 'CSV', 'HEAL VLMD CSV is the only currently supported input format.'

    with open(click.format_filename(input_file), 'r') as input:
        # dbGaP files are represented in XML as `data_table`s. We start by creating one.
        data_table = ETree.Element('data_table')

        # Write out the study_id.
        if not study_id:
            # If no study ID is provided, use the input filename.
            # TODO: once we support JSON, we can use either root['title'] or root['description'] here.
            study_id = os.path.basename(input_file)
        else:
            # Assume it is an HDP identifier, so add the HDP_ID_PREFIX.
            study_id = HDP_ID_PREFIX + study_id
        data_table.set('study_id', study_id)

        # Add the APPL ID.
        if appl_id:
            data_table.set('appl_id', appl_id)

        # Add the study title.
        # Note: not a dbGaP XML field! We make this up for communication.
        if study_name:
            data_table.set('study_name', study_name)

        # Record the creation date as this moment.
        data_table.set('date_created', datetime.now().isoformat())

        # Read input file and convert variables into
        if file_format == 'CSV':
            reader = csv.DictReader(input)

            # Some counts that are currently useful.
            counters = defaultdict(int)

            unique_variable_ids = set()
            for index, row in enumerate(reader):
                counters['row'] += 1
                row_index = index + 1  # Convert from zero-based index to one-based index.

                variable = ETree.SubElement(data_table, 'variable')

                # Variable name
                var_name = row.get('name')
                if not var_name:
                    logging.error(f"No variable name found in row on line {index + 1}, skipping.")
                    counters['no_varname'] += 1
                    continue
                counters['has_varname'] += 1
                # Make sure the variable ID is unique (by adding `_1`, `_2`, ... to the end of it).
                variable_index = 0
                while var_name in unique_variable_ids:
                    variable_index += 1
                    var_name = row['name'] + '_' + variable_index
                variable.set('id', var_name)
                if var_name != row['name']:
                    logging.warning(f"Duplicate variable ID detected for {row['name']}, so replaced it with "
                                    f"{var_name} -- note that the name element is unchanged.")
                name = ETree.SubElement(variable, 'name')
                name.text = var_name

                # Variable title
                # NOTE: this is not yet supported by Dug!
                if row.get('title'):
                    title = ETree.SubElement(variable, 'title')
                    title.text = row['title']
                    counters['has_title'] += 1
                else:
                    counters['no_title'] += 1

                # Variable description
                if row.get('description'):
                    desc = ETree.SubElement(variable, 'description')
                    desc.text = row['description']
                    counters['has_description'] += 1
                else:
                    counters['no_description'] += 1

                # Module (questionnaire/subsection name) Export the `module` field so that we can look for
                # instruments.
                #
                # TODO: this is a custom field. Instead of this, we could export each data dictionary as a separate
                # dbGaP file. Need to check to see what works better for Dug ingest.
                if row.get('module'):
                    variable.set('module', row['module'])
                    if 'module_counts' not in counters:
                        counters['module_counts'] = defaultdict(int)
                    counters['module_counts'][row['module']] += 1
                else:
                    counters['no_module'] += 1

                # Constraints

                # Minium and maximum values
                if row.get('constraints.maximum'):
                    logical_max = ETree.SubElement(variable, 'logical_max')
                    logical_max.text = str(row['constraints.maximum'])
                if row.get('constraints.minimum'):
                    logical_min = ETree.SubElement(variable, 'logical_min')
                    logical_min.text = str(row['constraints.minimum'])

                # Maximum length ('constraints.maxLength') is not supported in dbGaP XML, so we ignore it.

                # We ignore 'constraints.pattern' and 'format' for now, but we can try to include them in the
                # description later if that is useful.
                if row.get('constraints.pattern'):
                    counters['constraints.pattern'] += 1
                    logging.warning(f"`constraints.pattern` of {row['constraints.pattern']} found in row {row_index}, "
                                    f"but pattern constraints are not currently being written.")
                if row.get('format'):
                    counters['format'] += 1
                    logging.warning(f"Found `format` of {row['format']} found in row {row_index}, but format is not "
                                    f"currently being written.")

                # Process enumerated and encoded values.
                encs = {}
                if row.get('encodings'):
                    counters['encodings'] += 1

                    for encoding in re.split("\\s*\\|\\s*", row['encodings']):
                        m = re.fullmatch("^\\s*(.*?)\\s*=\\s*(.*)\\s*$", encoding)
                        if not m:
                            raise RuntimeError(
                                f"Could not parse encodings {row['encodings']} on row {row_index}")
                        key = m.group(1)
                        value = m.group(2)

                        if key in encs:
                            raise RuntimeError(
                                f"Duplicate key detected in encodings {row['encodings']} on row {row_index}")
                        encs[key] = value

                for key, value in encs.items():
                    value_element = ETree.SubElement(variable, 'value')
                    value_element.set('code', key)
                    value_element.text = value

                # Double-check encodings with constraints.enum
                if row.get('constraints.enum'):
                    enums = re.split("\\s*\\|\\s*", row['constraints.enum'])
                    if set(enums) != set(encs.keys()):
                        logging.error(f"`constraints.enum` ({row['constraints.enum']}) and `encodings` ({row['encodings']}) do not match.")
                        counters['enum_encoding_mismatch'] += 1

                # Variable type.
                typ = row.get('type')
                if encs:
                    typ = 'encoded value'
                if typ:
                    type_element = ETree.SubElement(variable, 'type')
                    type_element.text = typ

                # We currently ignore metadata fields not usually filled in for input VLMD files:
                # ordered, missingValues, trueValues, falseValues, repo_link

                # We currently ignore all standardMappings: standardsMappings.type, standardsMappings.label,
                # standardsMappings.url, standardsMappings.source, standardsMappings.id
                # We currently ignore all relatedConcepts: relatedConcepts.type, relatedConcepts.label,
                # relatedConcepts.url, relatedConcepts.source, relatedConcepts.id

                # We currently ignore all univarStats vars: univarStats.median, univarStats.mean, univarStats.std,
                # univarStats.min, univarStats.max, univarStats.mode, univarStats.count,
                # univarStats.twentyFifthPercentile, univarStats.seventyFifthPercentile,
                # univarStats.categoricalMarginals.name, univarStats.categoricalMarginals.count
        else:
            # This shouldn't be needed, since Click should catch any file format not in the accepted list.
            raise RuntimeError(f"Unsupported file format {file_format}")

        # Write out dbGaP XML.
        xml_str = ETree.tostring(data_table, encoding='unicode')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml()
        print(pretty_xml_str, file=output)

        # Display counters.
        logging.info(f"Counters: {json.dumps(counters, sort_keys=True, indent=2)}")


# Run vlmd_to_dbgap_xml() if not used as a library.
if __name__ == "__main__":
    vlmd_to_dbgap_xml()
