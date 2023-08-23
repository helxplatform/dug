#
# Script to download all data dictionaries from the HEAL Platform Metadata Service (MDS).
#
# USAGE:
#   python bin/get_heal_platform_mds_data_dicts.py
#
# If no MDS endpoint is specified, we default to the production endpoint at https://healdata.org/mds/metadata
#
import json
import os
import re
import click
import logging
import requests
from collections import defaultdict
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

# Some defaults.
DEFAULT_MDS_ENDPOINT = 'https://healdata.org/mds/metadata'
MDS_DEFAULT_LIMIT = 10000
DATA_DICT_GUID_TYPE = 'data_dictionary'
HDP_ID_PREFIX = 'HEALDATAPLATFORM:'

# Turn on logging
logging.basicConfig(level=logging.INFO)


def download_from_mds(studies_dir, data_dicts_dir, studies_with_data_dicts_dir, mds_metadata_endpoint, mds_limit):
    """
    Download all the studies and data dictionaries from the Platform MDS.
    (At the moment, we assume everything that isn't a data dictionary is a
    study).

    :param studies_dir: The directory into which to write the studies.
    :param data_dicts_dir: The directory into which to write the data dictionaries.
    :param studies_with_data_dicts_dir: The directory into which to write the studies with data dictionaries.
    :param mds_metadata_endpoint: The Platform MDS endpoint to use.
    :return: A dictionary of all the studies, with the study ID as keys.
    """

    # Download data dictionary identifiers. We filter using the DATA_DICT_GUID_TYPE provided earlier.
    # This allows us to download (and complain about) the data dictionaries that are not part of studies.
    #
    # TODO: extend this so it can function even if there are more than mds_limit data dictionaries.
    result = requests.get(mds_metadata_endpoint, params={
        '_guid_type': DATA_DICT_GUID_TYPE,
        'limit': mds_limit,
    })
    if not result.ok:
        raise RuntimeError(f'Could not retrieve data dictionary list: {result}')
    datadict_ids = result.json()
    logging.debug(f"Downloaded {len(datadict_ids)} data dictionaries.")

    # Download "studies" (everything that isn't a data dictionary). To do this, we download every metadata ID
    # (which we store in metadata_ids) and filter out the data dictionary identifiers we've seen before.
    #
    # TODO: extend this so it can function even if there are more than mds_limit data dictionaries.
    result = requests.get(mds_metadata_endpoint, params={
        'limit': mds_limit,
    })
    if not result.ok:
        raise RuntimeError(f'Could not retrieve metadata list: {result}')
    metadata_ids = result.json()
    study_ids = list(set(metadata_ids) - set(datadict_ids))

    # Download all the studies. This allows us to identify which study each data dictionary is connected to, and
    # allows us to complain about stray data dictionaries that are not connected to any study.
    #
    studies = {}
    studies_to_dds = defaultdict(list)
    for count, study_id in enumerate(study_ids):
        logging.debug(f"Downloading study {study_id} ({count + 1}/{len(study_ids)})")

        result = requests.get(mds_metadata_endpoint + '/' + study_id)
        if not result.ok:
            raise RuntimeError(f'Could not retrieve study ID {study_id}: {result}')

        result_json = result.json()

        # Record all the studies in case we need to look them up later.
        if study_id in studies:
            raise RuntimeError(f'Duplicate study ID: {study_id}')
        studies[study_id] = result_json

        # Record studies that have data dictionaries.
        if 'data_dictionaries' in result_json:
            dicts = result_json['data_dictionaries'].items()
            for (key, dd_id) in dicts:
                logging.info(f"Found data dictionary {key} in study {study_id}: {dd_id}")
                studies_to_dds[study_id].append({
                    'id': dd_id,
                    'label': key
                })

        # For debugging (and later Dug ingest), write the study-level metadata into the studies directory.
        with open(os.path.join(studies_dir, study_id + '.json'), 'w') as f:
            json.dump(result_json, f)

    logging.info(f"Downloaded {len(studies)} studies, of which {len(studies_to_dds)} studies have data dictionaries.")

    # For studies containing data dictionaries, write them into data_dicts_dir, but after adding a
    # `data_dictionaries` key that has a list of the data dictionaries associated with it, which we
    # download separately from the MDS.
    data_dict_ids_within_studies = set()
    for count, study_id in enumerate(studies_to_dds.keys()):
        logging.debug(f"Adding data dictionaries to study {study_id} ({count + 1}/{len(studies_to_dds)})")

        study_json = studies[study_id]
        study_json['data_dictionaries'] = []

        for dd in studies_to_dds[study_id]:
            dd_id = dd['id']
            dd_label = dd['label']

            result = requests.get(mds_metadata_endpoint + '/' + dd_id)
            if result.status_code == 404:
                logging.warning(
                    f"Study {study_id} refers to data dictionary {dd_id}, but no such data dictionary was found in "
                    f"the MDS.")
                result_json = {'error': result.json()}
            elif not result.ok:
                raise RuntimeError(f'Could not retrieve data dictionary {dd_id}: {result}')
            else:
                data_dict_ids_within_studies.add(dd_id)
                result_json = result.json()
                result_json['@id'] = dd_id
                result_json['label'] = dd_label

            study_json['data_dictionaries'].append(result_json)

        # Write out the data dictionaries.
        with open(os.path.join(studies_with_data_dicts_dir, study_id + '.json'), 'w') as f:
            json.dump(study_json, f)

        logging.debug(
            f"Wrote {len(study_json['data_dictionaries'])} dictionaries to {studies_with_data_dicts_dir}/{study_id}.json")

    # We shouldn't need to do this, but at the moment we have multiple data dictionaries (in pre-prod, not prod) that aren't linked to from
    # within studies. So let's download them separately!
    data_dict_ids_not_within_studies = list(set(datadict_ids) - data_dict_ids_within_studies)
    for count, dd_id in enumerate(data_dict_ids_not_within_studies):
        dd_id_json_path = os.path.join(data_dicts_dir, dd_id.replace('/', '_') + '.json')

        logging.debug(
            f"Downloading data dictionary not linked to a study {dd_id} ({count + 1}/{len(data_dict_ids_not_within_studies)})")

        result = requests.get(mds_metadata_endpoint + '/' + dd_id)
        if not result.ok:
            raise RuntimeError(f'Could not retrieve data dictionary {dd_id}: {result}')

        data_dict_json = result.json()
        data_dict_json['@id'] = dd_id
        with open(dd_id_json_path, 'w') as f:
            json.dump(data_dict_json, f)

        logging.debug(f"Wrote data dictionary to {dd_id_json_path}.json")

    if len(data_dict_ids_not_within_studies) > 0:
        logging.warning(f"Some data dictionaries ({len(data_dict_ids_not_within_studies)}are present in the Platform "
                        f"MDS, but aren't associated with studies: {data_dict_ids_not_within_studies}")

    # Return the list of studies and the studies with data dictionaries.
    return study_ids, data_dict_ids_within_studies


def generate_dbgap_files(dbgap_dir, studies_with_data_dicts_dir):
    """
    Generate dbGaP files from data dictionaries containing

    :param dbgap_dir: The dbGaP directory into which we write the dbGaP files.
    :param studies_with_data_dicts_dir: The directory that contains studies containing data dictionaries.
        (This should work for the data_dicts directory too, but then we have no way of linking them to studies.)
    :return: The list of dbGaP files generated.
    """

    dbgap_files_generated = set()

    data_dict_files = os.listdir(studies_with_data_dicts_dir)
    for data_dict_file in data_dict_files:
        file_path = os.path.join(studies_with_data_dicts_dir, data_dict_file)

        # We're only interested in files.
        if not os.path.isfile(file_path):
            continue

        # We're only interested in JSON files.
        if not file_path.lower().endswith('.json'):
            continue

        # Read the JSON file.
        logging.info(f"Loading study containing data dictionaries: {file_path}")
        with open(file_path, 'r') as f:
            json_data = json.load(f)

        # Check if this contains data dictionaries or if it _is_ a data dictionary.
        # (This is not currently used, but the idea is that you could call this function on
        # the data_dict directory instead of the studies_with_data_dicts directory and generate
        # dbGaP XML files for all of them instead.
        data_dicts = []
        if 'data_dictionaries' in json_data:
            data_dicts = json_data['data_dictionaries']
            study = json_data
        elif 'data_dictionary' in json_data:
            data_dicts = [json_data['data_dictionary']]
            study = {}
        else:
            raise RuntimeError(f"Could not read {file_path}: unknown format.")

        # Begin writing a dbGaP file for each data dictionary.
        for data_dict in data_dicts:
            # A list of unique variable identifiers in this data dictionary file.
            # If you need to make sure every variable from MDS is uniquely identified, you can move this set to the
            # top-level of this file.
            unique_variable_ids = set()

            data_table = ET.Element('data_table')

            if 'gen3_discovery' in study:
                # Every data dictionary from the HEAL Data Platform should have an ID, and the previous code should have
                # stored it in the `@id` field in the data dictionary JSON file.
                #
                # There may also be a `label`, which is the key of the data dictionary in the study.
                if '@id' in study['gen3_discovery']:
                    data_table.set('id', study['gen3_discovery']['@id'])
                else:
                    logging.warning(f"No identifier found in data dictionary file {file_path}")

                if 'label' in study['gen3_discovery']:
                    data_table.set('label', study['gen3_discovery']['label'])

                # Determine the data_table study_id from the internal HEAL Data Platform (HDP) identifier.
                if '_hdp_uid' in study['gen3_discovery']:
                    data_table.set('study_id', HDP_ID_PREFIX + study['gen3_discovery']['_hdp_uid'])
                else:
                    logging.warning(f"No HDP ID found in data dictionary file {file_path}")

                # Create a non-standard appl_id field just in case we need it later.
                # This should be fine for now, but there is also a `comments` element that we can
                # store information like this in if we need to.
                if 'appl_id' in study['gen3_discovery']:
                    data_table.set('appl_id', study['gen3_discovery']['appl_id'])
                else:
                    logging.warning(f"No APPL ID found in data dictionary file {file_path}")

                # Determine the data_table date_created
                if 'date_added' in study['gen3_discovery']:
                    data_table.set('date_created', study['gen3_discovery']['date_added'])
                else:
                    logging.warning(f"No date_added found in data dictionary file {file_path}")

            if isinstance(data_dict, list):
                top_level_dict = {}
                second_tier_dicts = data_dict
            elif isinstance(data_dict, dict) and 'data_dictionary' in data_dict:
                top_level_dict = data_dict
                second_tier_dicts = data_dict['data_dictionary']
            else:
                raise RuntimeError(
                    f"Could not read {file_path}: list of data dictionaries not as expected: {data_dict}")

            for var_dict in second_tier_dicts:
                logging.debug(f"Generating dbGaP for variable {var_dict} in {file_path}")

                # Retrieve the variable name.
                variable = ET.SubElement(data_table, 'variable')

                # Make sure the variable ID is unique (by adding `_1`, `_2`, ... to the end of it).
                var_name = var_dict['name']
                variable_index = 0
                while var_name in unique_variable_ids:
                    variable_index += 1
                    var_name = var_dict['name'] + '_' + variable_index
                variable.set('id', var_name)
                if var_name != var_dict['name']:
                    logging.warning(f"Duplicate variable ID detected for {var_dict['name']}, so replaced it with "
                                    f"{var_name} -- note that the name element is unchanged.")

                # Create a name element for the variable. We don't uniquify this field.
                name = ET.SubElement(variable, 'name')
                name.text = var_name

                if 'description' in var_dict:
                    desc = ET.SubElement(variable, 'description')
                    desc.text = var_dict['description']

                # Export the `module` field so that we can look for instruments.
                # TODO: this is a custom field. Instead of this, we could export each data dictionary as a separate dbGaP
                # file. Need to check to see what works better for Dug ingest.
                if 'module' in var_dict:
                    variable.set('module', var_dict['module'])

                # Add constraints.
                if 'constraints' in var_dict:
                    # Check for minimum and maximum constraints.
                    if 'minimum' in var_dict['constraints']:
                        logical_min = ET.SubElement(variable, 'logical_min')
                        logical_min.text = str(var_dict['constraints']['minimum'])
                    if 'maximum' in var_dict['constraints']:
                        logical_max = ET.SubElement(variable, 'logical_max')
                        logical_max.text = str(var_dict['constraints']['maximum'])

                    # Determine a type for this variable.
                    typ = var_dict.get('type')
                    if 'enum' in var_dict['constraints'] and len(var_dict['constraints']['enum']) > 0:
                        typ = 'encoded value'
                    if typ:
                        type_element = ET.SubElement(variable, 'type')
                        type_element.text = typ

                # If there are encodings, we need to convert them into values.
                if 'encodings' in var_dict:
                    encs = {}
                    for encoding in re.split("\\s*\\|\\s*", var_dict['encodings']):
                        m = re.fullmatch("^\\s*(.*?)\\s*=\\s*(.*)\\s*$", encoding)
                        if not m:
                            raise RuntimeError(
                                f"Could not parse encodings {var_dict['encodings']} in data dictionary file {file_path}")
                        key = m.group(1)
                        value = m.group(2)
                        if key in encs:
                            raise RuntimeError(
                                f"Duplicate key detected in encodings {var_dict['encodings']} in data dictionary file {file_path}")
                        encs[key] = value

                    for key, value in encs.items():
                        value_element = ET.SubElement(variable, 'value')
                        value_element.set('code', key)
                        value_element.text = value

            # Write out XML.
            xml_str = ET.tostring(data_table, encoding='unicode')
            pretty_xml_str = minidom.parseString(xml_str).toprettyxml()

            # Produce the XML file by changing the .json to .xml.
            output_xml_filename = os.path.join(dbgap_dir, data_dict_file.replace('.json', '.xml'))
            with open(output_xml_filename, 'w') as f:
                f.write(pretty_xml_str)
            logging.info(f"Writing {data_table} to {output_xml_filename}")

            # Make a list of dbGaP files to report to the main program.
            dbgap_files_generated.add(output_xml_filename)

    return dbgap_files_generated


# Set up command line arguments.
@click.command()
@click.argument('output', type=click.Path(exists=False), required=True)
@click.option('--mds-metadata-endpoint', '--mds', default=DEFAULT_MDS_ENDPOINT,
              help='The MDS metadata endpoint to use, e.g. https://healdata.org/mds/metadata')
@click.option('--limit', default=MDS_DEFAULT_LIMIT, help='The maximum number of entries to retrieve from the Platform '
                                                         'MDS. Note that some MDS instances have their own built-in '
                                                         'limit; if you hit that limit, you will need to update the '
                                                         'code to support offsets.')
def get_heal_platform_mds_data_dicts(output, mds_metadata_endpoint, limit):
    """
    Retrieves files from the HEAL Platform Metadata Service (MDS) in a format that Dug can index,
    which at the moment is the dbGaP XML format (as described in https://ftp.ncbi.nlm.nih.gov/dbgap/dtd/).

    Creates the output directory, and then creates three directories in this directory:

      - studies/[study ID (appl)].json: All the studies in the HEAL Platform MDS.

      - datadicts/[data dictionary ID].json: All the data dictionaries in the HEAL Platform MDS.

      - dbGaPs/[data dictionary ID].xml: All the data dictionaries in the HEAL Platform MDS, converted into dbGaP XML format.

    Since other projects also use the Gen3 Metadata Service (MDS), one of our lesser goals here is to
    build code that could be quickly rewritten for other MDS schemas.

    :param output: The output directory, which should not exist when the script is run.
    """

    # Don't allow the program to run if the output directory already exists.
    if os.path.exists(output):
        logging.error(
            f"To ensure that existing data is not partially overwritten, the specified output directory ({output}) must not exist.")
        exit(1)

    # Create the output directory.
    os.makedirs(output, exist_ok=True)

    # Download studies and data dictionaries from the MDS endpoint. We create a lot of directories and temp files to
    # help with debugging -- we can simplify this later on if needed.
    studies_dir = os.path.join(output, 'studies')
    os.makedirs(studies_dir, exist_ok=True)
    data_dicts_dir = os.path.join(output, 'data_dicts')
    os.makedirs(data_dicts_dir, exist_ok=True)
    studies_with_data_dicts_dir = os.path.join(output, 'studies_with_data_dicts')
    os.makedirs(studies_with_data_dicts_dir, exist_ok=True)
    download_from_mds(studies_dir, data_dicts_dir, studies_with_data_dicts_dir, mds_metadata_endpoint, limit)

    # Generate dbGaP entries from the studies and the data dictionaries.
    dbgap_dir = os.path.join(output, 'dbGaPs')
    os.makedirs(dbgap_dir, exist_ok=True)

    dbgap_filenames = generate_dbgap_files(dbgap_dir, studies_with_data_dicts_dir)
    logging.info(f"Generated {len(dbgap_filenames)} dbGaP files for ingest in {dbgap_dir}.")


# Run get_heal_platform_mds_data_dicts() if not used as a library.
if __name__ == "__main__":
    get_heal_platform_mds_data_dicts()
