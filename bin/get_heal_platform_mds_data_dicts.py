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

import os
import click
import logging

# Some defaults.
DEFAULT_MDS_ENDPOINT = 'https://healdata.org/mds/metadata'

# Turn on logging
logging.basicConfig(level=logging.INFO)

# Set up command line arguments.
def download_studies(studies_dir, mds_metadata_endpoint):
    pass


def download_data_dicts(data_dicts_dir, studies_dir, mds_metadata_endpoint):
    pass


def generate_dbgap_files(dbgap_dir, data_dict_ids, data_dicts_dir, studies, mds_metadata_endpoint):
    return []


@click.command()
@click.argument('output', type=click.Path(), required=True) # TODO: restore exists=False once we're done developing.
@click.option('--mds-metadata-endpoint', '--mds', default=DEFAULT_MDS_ENDPOINT, help='The MDS metadata endpoint to use, e.g. https://healdata.org/mds/metadata')
def get_heal_platform_mds_data_dicts(output, mds_metadata_endpoint):
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

    # Download studies from MDS endpoint.
    studies_dir = os.path.join(output, 'studies')
    os.makedirs(studies_dir, exist_ok=True)
    studies = download_studies(studies_dir, mds_metadata_endpoint)

    # Download data dictionaries from MDS endpoint.
    data_dicts_dir = os.path.join(output, 'datadicts')
    os.makedirs(data_dicts_dir, exist_ok=True)
    data_dict_ids = download_data_dicts(data_dicts_dir, studies_dir, mds_metadata_endpoint)

    # Generate dbGaP entries from the studies and the data dictionaries.
    dbgap_dir = os.path.join(output, 'dbGaPs')
    os.makedirs(dbgap_dir, exist_ok=True)
    dbgap_filenames = generate_dbgap_files(dbgap_dir, data_dict_ids, data_dicts_dir, studies, mds_metadata_endpoint)

    logging.info(f"Generated {len(dbgap_filenames)} dbGaP files for ingest in {dbgap_dir}.")


# Run get_heal_platform_mds_data_dicts() if not used as a library.
if __name__ == "__main__":
    get_heal_platform_mds_data_dicts()