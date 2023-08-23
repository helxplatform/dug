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
import json
import os
import re
import sys
from datetime import datetime

import click
import logging
import requests
from collections import defaultdict
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

# Some defaults.
HDP_ID_PREFIX = 'HEALDATAPLATFORM:'

# Turn on logging
logging.basicConfig(level=logging.INFO)


# Set up command line arguments.
@click.command()
@click.argument('input_file', type=click.Path(exists=True), required=True)
@click.option('--file-format', '--format', type=click.Choice(['CSV'], case_sensitive=False), default='CSV')
@click.option('--output', '-o', type=click.File(mode='w'), default=sys.stdout)
@click.option('--study-id', type=str)
@click.option('--appl-id', type=str)
def vlmd_to_dbgap_xml(input_file, output, file_format, study_id, appl_id):
    """
    Convert a VLMD file into a dbGaP XML file for ingest into Dug.

    :param input_file: The VLMD file to read.
    :param output: Where the dbGaP XML file should be written.
    :param file_format: The file format to read. Only [HEAL VLMD] 'CSV' is currently supported.
    :param study_id: The HEAL Data Platform Study ID to use in Dug (without a prefix).
    :param appl_id: The APPL ID to use in Dug.
    """

    assert file_format == 'CSV', 'HEAL VLMD CSV is the only currently supported input format.'

    with open(click.format_filename(input_file), 'r') as input:
        # dbGaP files are represented in XML as data_tables. We start by creating one.
        data_table = ET.Element('data_table')

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

        data_table.set('date_created', datetime.now().isoformat())

        # Convert variables.
        #
        # if 'gen3_discovery' in study:
        #     # Every data dictionary from the HEAL Data Platform should have an ID, and the previous code should have
        #     # stored it in the `@id` field in the data dictionary JSON file.
        #     #
        #     # There may also be a `label`, which is the key of the data dictionary in the study.
        #     if '@id' in study['gen3_discovery']:
        #         data_table.set('id', study['gen3_discovery']['@id'])
        #     else:
        #         logging.warning(f"No identifier found in data dictionary file {file_path}")
        #
        #     if 'label' in study['gen3_discovery']:
        #         data_table.set('label', study['gen3_discovery']['label'])
        #
        #     # Determine the data_table study_id from the internal HEAL Data Platform (HDP) identifier.
        #     if '_hdp_uid' in study['gen3_discovery']:
        #         data_table.set('study_id', HDP_ID_PREFIX + study['gen3_discovery']['_hdp_uid'])
        #     else:
        #         logging.warning(f"No HDP ID found in data dictionary file {file_path}")
        #
        #     # Create a non-standard appl_id field just in case we need it later.
        #     # This should be fine for now, but there is also a `comments` element that we can
        #     # store information like this in if we need to.
        #     if 'appl_id' in study['gen3_discovery']:
        #         data_table.set('appl_id', study['gen3_discovery']['appl_id'])
        #     else:
        #         logging.warning(f"No APPL ID found in data dictionary file {file_path}")
        #
        #     # Determine the data_table date_created
        #     if 'date_added' in study['gen3_discovery']:
        #         data_table.set('date_created', study['gen3_discovery']['date_added'])
        #     else:
        #         logging.warning(f"No date_added found in data dictionary file {file_path}")
        #
        # if isinstance(data_dict, list):
        #     top_level_dict = {}
        #     second_tier_dicts = data_dict
        # elif isinstance(data_dict, dict) and 'data_dictionary' in data_dict:
        #     top_level_dict = data_dict
        #     second_tier_dicts = data_dict['data_dictionary']
        # else:
        #     raise RuntimeError(
        #         f"Could not read {file_path}: list of data dictionaries not as expected: {data_dict}")
        #
        # for var_dict in second_tier_dicts:
        #     logging.debug(f"Generating dbGaP for variable {var_dict} in {file_path}")
        #
        #     # Retrieve the variable name.
        #     variable = ET.SubElement(data_table, 'variable')
        #
        #     # Make sure the variable ID is unique (by adding `_1`, `_2`, ... to the end of it).
        #     var_name = var_dict['name']
        #     variable_index = 0
        #     while var_name in unique_variable_ids:
        #         variable_index += 1
        #         var_name = var_dict['name'] + '_' + variable_index
        #     variable.set('id', var_name)
        #     if var_name != var_dict['name']:
        #         logging.warning(f"Duplicate variable ID detected for {var_dict['name']}, so replaced it with "
        #                         f"{var_name} -- note that the name element is unchanged.")
        #
        #     # Create a name element for the variable. We don't uniquify this field.
        #     name = ET.SubElement(variable, 'name')
        #     name.text = var_name
        #
        #     if 'description' in var_dict:
        #         desc = ET.SubElement(variable, 'description')
        #         desc.text = var_dict['description']
        #
        #     # Export the `module` field so that we can look for instruments.
        #     # TODO: this is a custom field. Instead of this, we could export each data dictionary as a separate dbGaP
        #     # file. Need to check to see what works better for Dug ingest.
        #     if 'module' in var_dict:
        #         variable.set('module', var_dict['module'])
        #
        #     # Add constraints.
        #     if 'constraints' in var_dict:
        #         # Check for minimum and maximum constraints.
        #         if 'minimum' in var_dict['constraints']:
        #             logical_min = ET.SubElement(variable, 'logical_min')
        #             logical_min.text = str(var_dict['constraints']['minimum'])
        #         if 'maximum' in var_dict['constraints']:
        #             logical_max = ET.SubElement(variable, 'logical_max')
        #             logical_max.text = str(var_dict['constraints']['maximum'])
        #
        #         # Determine a type for this variable.
        #         typ = var_dict.get('type')
        #         if 'enum' in var_dict['constraints'] and len(var_dict['constraints']['enum']) > 0:
        #             typ = 'encoded value'
        #         if typ:
        #             type_element = ET.SubElement(variable, 'type')
        #             type_element.text = typ
        #
        #     # If there are encodings, we need to convert them into values.
        #     if 'encodings' in var_dict:
        #         encs = {}
        #         for encoding in re.split("\\s*\\|\\s*", var_dict['encodings']):
        #             m = re.fullmatch("^\\s*(.*?)\\s*=\\s*(.*)\\s*$", encoding)
        #             if not m:
        #                 raise RuntimeError(
        #                     "Could not parse encodings {var_dict['encodings']} in data dictionary file {file_path}")
        #             key = m.group(1)
        #             value = m.group(2)
        #             if key in encs:
        #                 raise RuntimeError(
        #                     f"Duplicate key detected in encodings {var_dict['encodings']} in data dictionary file {file_path}")
        #             encs[key] = value
        #
        #         for key, value in encs.items():
        #             value_element = ET.SubElement(variable, 'value')
        #             value_element.set('code', key)
        #             value_element.text = value
        #
        # # Write out XML.
        # xml_str = ET.tostring(data_table, encoding='unicode')
        # pretty_xml_str = minidom.parseString(xml_str).toprettyxml()
        #
        # # Produce the XML file by changing the .json to .xml.
        # output_xml_filename = os.path.join(dbgap_dir, data_dict_file.replace('.json', '.xml'))
        # with open(output_xml_filename, 'w') as f:
        #     f.write(pretty_xml_str)
        # logging.info(f"Writing {data_table} to {output_xml_filename}")
        #
        # # Make a list of dbGaP files to report to the main program.
        # dbgap_files_generated.add(output_xml_filename)

        # Write out dbGaP XML.
        xml_str = ET.tostring(data_table, encoding='unicode')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml()
        print(pretty_xml_str, file=output)


# Run vlmd_to_dbgap_xml() if not used as a library.
if __name__ == "__main__":
    vlmd_to_dbgap_xml()
