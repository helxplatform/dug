#
# Script to download the list of BDC studies from Gen3 (using it as a source of truth).
#
# USAGE:
#   python bin/get_bdc_studies_from_gen3.py output.csv
#
# The BDC Gen3 instance is hosted at https://gen3.biodatacatalyst.nhlbi.nih.gov/
#
import csv
import json
import logging
import os
import re
import sys
import urllib.parse
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ETree
from collections import defaultdict, Counter
from datetime import datetime

import click
import requests

# Configuration
# The number of items to download at a single go. This is usually capped by the Gen3 instance, so you need to make sure
# that this limit is lower than theirs!
GEN3_DOWNLOAD_LIMIT = 50

# Turn on logging
logging.basicConfig(level=logging.INFO)


def download_gen3_list(input_url, download_limit=GEN3_DOWNLOAD_LIMIT):
    """
    This function helps download a list of items from Gen3 by downloading the list and -- as long as there are
    as many items as the download_limit -- by using `offset` to get the next set of results.

    :param input_url: The URL to download. This function will concatenate `&limit=...&offset=...` to it, so it should
    end with arguments or at least a question mark.

    :param download_limit: The maximum number of items to download (as set by `limit=...`). Note that Gen3 has an
    internal limit, so you should make sure your limit is smaller than that -- otherwise, you will request e.g. 3000
    entries but retrieve the Gen3 limit (say, 2000), which this function will interpret to mean that all entries have
    been downloaded.

    :return: A list of retrieved strings. (This function only works when the result is a simple JSON list of strings.)
    """
    complete_list = []
    offset = 0
    while True:
        url = input_url + f"&limit={download_limit}&offset={offset}"
        logging.debug(f"Requesting GET {url} from Gen3")
        partial_list_response = requests.get(url)
        if not partial_list_response.ok:
            raise RuntimeError(f"Could not download discovery_metadata from BDC Gen3 {url}: " +
                               f"{partial_list_response.status_code} {partial_list_response.text}")

        partial_list = partial_list_response.json()
        complete_list.extend(partial_list)
        if len(partial_list) < GEN3_DOWNLOAD_LIMIT:
            # No more entries to download!
            break

        # Otherwise, increment offset by DOWNLOAD_SIZE
        offset += download_limit

    # Make sure we don't have duplicates -- this is more likely to be an error in the offset algorithm than an actual
    # error.
    if len(complete_list) != len(set(complete_list)):
        duplicate_ids = sorted([ident for ident, count in Counter(complete_list).items() if count > 1])
        logging.warning(f"Found duplicate discovery_metadata: {duplicate_ids}")

    return complete_list


# Set up command line arguments.
@click.command()
@click.argument('output', type=click.File('w'), required=True)
@click.option('--bdc-gen3-base-url',
              help='The base URL of the BDC Gen3 instance (before `/mds/...`)',
              type=str,
              metavar='URL',
              default='https://gen3.biodatacatalyst.nhlbi.nih.gov/')
def get_bdc_studies_from_gen3(output, bdc_gen3_base_url):
    """
    Retrieve BDC studies from the BDC Gen3 Metadata Service (MDS) instance and write them out as a CSV file to OUTPUT_FILE
    for get_dbgap_data_dicts.py to use.
    \f
    # \f truncates the help text as per https://click.palletsprojects.com/en/8.1.x/documentation/#truncating-help-texts

    :param output: The CSV file to be generated.
    :param bdc_gen3_base_url: The BDC Gen3 base URL (i.e. everything before the `/mds/...`). Defaults to
        https://gen3.biodatacatalyst.nhlbi.nih.gov/.
    """

    # Step 1. Download all the discovery_metadata from the BDC Gen3 Metadata Service (MDS).
    mds_discovery_metadata_url = urllib.parse.urljoin(
        bdc_gen3_base_url,
        f'/mds/metadata?_guid_type=discovery_metadata'
    )

    logging.debug(f"Downloading study identifiers from MDS discovery metadata URL: {mds_discovery_metadata_url}.")
    discovery_list = download_gen3_list(mds_discovery_metadata_url, download_limit=GEN3_DOWNLOAD_LIMIT)
    logging.info(f"Downloaded {len(discovery_list)} discovery_metadata from BDC Gen3 with a limit of {GEN3_DOWNLOAD_LIMIT}.")
    sorted_study_ids = sorted(discovery_list)

    # Step 2. For every study ID, write out an entry into the CSV output file.
    csv_writer = csv.DictWriter(output, fieldnames=['Accession', 'Consent', 'Study Name', 'Program', 'Last modified', 'Notes', 'Description'])
    csv_writer.writeheader()
    for study_id in sorted_study_ids:
        # Reset the variables we need.
        study_name = ''
        program_names = []
        description = ''
        notes = ''

        # Gen3 doesn't have a last-modified date. We could eventually try to download that directly from dbGaP (but why?),
        # but it's easier to use the current date.
        last_modified = str(datetime.now().date())

        # Download study information.
        url = urllib.parse.urljoin(bdc_gen3_base_url, f'/mds/metadata/{study_id}')
        study_info_response = requests.get(url)
        if not study_info_response.ok:
            raise RuntimeError(f"Could not download study information about study {study_id} at URL {url}.")

        study_info = study_info_response.json()
        if 'gen3_discovery' in study_info:
            gen3_discovery = study_info['gen3_discovery']

            # We prefer full_name to name, which is often identical to the short name.
            if 'full_name' in gen3_discovery:
                study_name = gen3_discovery['full_name']
                notes += f"Name: {gen3_discovery.get('name', '')}, short name: {gen3_discovery.get('short_name', '')}.\n"
            elif 'name' in gen3_discovery:
                study_name = gen3_discovery['name']
                notes += f"Short name: {gen3_discovery.get('short_name', '')}.\n"
            elif 'short_name' in gen3_discovery:
                study_name = gen3_discovery['short_name']
            else:
                study_name = '(no name)'

            # Program name.
            if 'tags' in gen3_discovery:
                for tag in gen3_discovery['tags']:
                    category = tag.get('category', '')
                    if category.lower() == 'program':
                        program_names.append(tag.get('name', '').strip())

            # Description.
            description = gen3_discovery.get('study_description', '')

        # Extract accession and consent.
        m = re.match(r'^(phs.*?)(?:\.(c\d+))?$', study_id)
        if not m:
            logging.warning(f"Skipping study_id '{study_id}' as non-dbGaP identifiers are not currently supported by "
                            f"Dug.")
            continue

        if m.group(2):
            accession = m.group(1)
            consent = m.group(2)
        else:
            accession = study_id
            consent = ''

        # Remove any blank program names.
        program_names = sorted(filter(lambda n: n != '', program_names))

        csv_writer.writerow({
            'Accession': accession,
            'Consent': consent,
            'Study Name': study_name,
            'Description': description,
            'Program': '|'.join(program_names),
            'Last modified': last_modified,
            'Notes': notes.strip()
        })

    exit(0)

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
                    logging.warning(f"`constraints.pattern` of {row['constraints.pattern']} found in row {row_index}, skipped.")
                if row.get('format'):
                    counters['format'] += 1
                    logging.warning(f"Found `format` of {row['format']} found in row {row_index}, skipped.")

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


# Run get_bdc_studies_from_gen3() if not used as a library.
if __name__ == "__main__":
    get_bdc_studies_from_gen3()
