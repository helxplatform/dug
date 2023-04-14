#
# Script to download all HEAL Platform
#
# USAGE:
#   HEAL_PLATFORM_MDS_ENDPOINT=https://healdata.org/mds/metadata python bin/get_heal_platform_mds_data_dicts.py [--output-dir OUTPUT_DIR]
#
# If no HEAL_PLATFORM_MDS_ENDPOINT is specified, we default to the production endpoint at https://healdata.org/mds/metadata
# If no OUTPUT_DIR is specified, we default to the `data/heal_platform_mds` directory in this repository.
#
# This code was written with the assistance of ChatGPT (https://help.openai.com/en/articles/6825453-chatgpt-release-notes).
#
import json
import os
import click
import logging
import requests
import urllib

# Some defaults.
DEFAULT_MDS_ENDPOINT = 'https://healdata.org/mds/metadata'
MDS_DEFAULT_LIMIT = 10000
DATA_DICT_GUID_TYPE = 'data_dictionary'

# Turn on logging
logging.basicConfig(level=logging.DEBUG)


def download_from_mds(studies_dir, data_dicts_dir, mds_metadata_endpoint, mds_limit):
    """
    Download all the studies and data dictionaries from the Platform MDS.
    (At the moment, we assume everything that isn't a data dictionary is a
    study).

    :param studies_dir: The directory into which to write the studies.
    :param data_dicts_dir: The directory into which to write the data dictionaries.
    :param mds_metadata_endpoint: The Platform MDS endpoint to use.
    :return: A dictionary of all the studies, with the study ID as keys.
    """

    # Download data dictionary identifiers.
    # TODO: extend this so it can function even if there are more than mds_limit data dictionaries.
    result = requests.get(mds_metadata_endpoint, params={
        '_guid_type': DATA_DICT_GUID_TYPE,
        'limit': mds_limit,
    })
    if not result.ok:
        raise RuntimeError(f'Could not retrieve data dictionary list: {result}')

    datadict_ids = result.json()

    logging.debug(f"Downloaded {len(datadict_ids)} data dictionaries.")

    # Download "studies" (everything that isn't a data dictionary).
    result = requests.get(mds_metadata_endpoint, params={
        'limit': mds_limit,
    })
    if not result.ok:
        raise RuntimeError(f'Could not retrieve metadata list: {result}')

    metadata_ids = result.json()
    study_ids = list(set(metadata_ids) - set(datadict_ids))

    # Download studies.
    studies_by_appl = {}
    studies_with_dds =
    for count, study_id in enumerate(study_ids):
        logging.debug(f"Downloading study {study_id} ({count + 1}/{len(study_ids)})")

        result = requests.get(mds_metadata_endpoint + '/' + study_id)
        if not result.ok:
            raise RuntimeError(f'Could not retrieve study ID {study_id}: {result}')

        result_json = result.json()

        if study_id in studies_by_appl:
            raise RuntimeError(f'Duplicate study ID: {study_id}')
        studies_by_appl[study_id] = result_json

        with open(os.path.join(studies_dir, study_id + '.json'), 'w') as f:
            json.dump(result_json, f)

def generate_dbgap_files(dbgap_dir, data_dict_ids, data_dicts_dir, studies, mds_metadata_endpoint):
    return []


# Set up command line arguments.
@click.command()
@click.argument('output', type=click.Path(), required=True) # TODO: restore exists=False once we're done developing.
@click.option('--mds-metadata-endpoint', '--mds', default=DEFAULT_MDS_ENDPOINT, help='The MDS metadata endpoint to use, e.g. https://healdata.org/mds/metadata')
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

    # Create the output directory.
    os.makedirs(output, exist_ok=True)

    # Download studies and data dictionaries from the MDS endpoint.
    studies_dir = os.path.join(output, 'studies')
    os.makedirs(studies_dir, exist_ok=True)
    data_dicts_dir = os.path.join(output, 'data_dicts')
    os.makedirs(data_dicts_dir, exist_ok=True)
    studies = download_from_mds(studies_dir, data_dicts_dir, mds_metadata_endpoint, limit)

    # Generate dbGaP entries from the studies and the data dictionaries.
    dbgap_dir = os.path.join(output, 'dbGaPs')
    os.makedirs(dbgap_dir, exist_ok=True)
    dbgap_filenames = generate_dbgap_files(dbgap_dir, data_dict_ids, data_dicts_dir, studies, mds_metadata_endpoint)

    logging.info(f"Generated {len(dbgap_filenames)} dbGaP files for ingest in {dbgap_dir}.")


# Run get_heal_platform_mds_data_dicts() if not used as a library.
if __name__ == "__main__":
    get_heal_platform_mds_data_dicts()