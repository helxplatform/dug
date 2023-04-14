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

import click
import logging

# Turn on logging
logging.basicConfig(level=logging.INFO)

# Set up command line arguments.
@click.command()
@click.argument('output', type=click.Path(exists=False), required=True)
def get_heal_platform_mds_data_dicts(output):
    """
    Retrieves files from the HEAL Platform Metadata Service (MDS) in a format that Dug can index,
    which at the moment is the dbGaP XML format (as described in https://ftp.ncbi.nlm.nih.gov/dbgap/dtd/).

    Creates the output directory, and then creates three directories in this directory:

      - studies/[study ID (appl)].json: All the studies in the HEAL Platform MDS.

      - datadicts/[data dictionary ID].json: All the data dictionaries in the HEAL Platform MDS.

      - dbGaP/[data dictionary ID].xml: All the data dictionaries in the HEAL Platform MDS, converted into dbGaP XML format.

    Since other projects also use the Gen3 Metadata Service (MDS), one of our lesser goals here is to
    build code that could be quickly rewritten for other MDS schemas.

    :param output: The output directory, which should not exist when the script is run.
    """
    print(f"Output directory: ${output}")


# Run get_heal_platform_mds_data_dicts() if not used as a library.
if __name__ == "__main__":
    get_heal_platform_mds_data_dicts()