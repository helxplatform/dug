####### ANVIL Syncing Script

# This script is used to generate the input to index Anvil Datasets on Dug
# Parse, Download dbgap datasets currently hosted on Anvil Platform (tsv downloaded from https://anvilproject.org/data)
# Output all datasets to an output tarball into the data directory to be indexed
# NOTE: The ncpi-dataset-catalog-results.tsv should be updated manually to ensure you sync all current Anvil datasets

#######

import os
import shutil
from ftplib import FTP, error_perm
import csv

# Hard-coded relative paths for the anvil catalog input file and output bolus
# This obviously isn't very elegant but it'll do for now
input_file = "../data/ncpi-dataset-catalog-results.tsv"
output_dir = "../data/"


# Helper function
def download_dbgap_study(study_id, output_dir):
    # Download a dbgap study to a specific directory

    ftp = FTP('ftp.ncbi.nlm.nih.gov')
    ftp.login()
    study_variable = study_id.split('.')[0]
    os.makedirs(f"{output_dir}/{study_id}")

    # Step 1: First we try and get all the data_dict files
    try:
        ftp.cwd(f"/dbgap/studies/{study_variable}/{study_id}/pheno_variable_summaries")
    except error_perm:
        print(f"WARN: Unable to find data dicts for study: {study_id}")
        # Delete subdirectory so we don't think it's full
        shutil.rmtree(f"{output_dir}/{study_id}")
        return False

    ftp_filelist = ftp.nlst(".")
    for ftp_filename in ftp_filelist:
        if 'data_dict' in ftp_filename:
            with open(f"{output_dir}/{study_id}/{ftp_filename}", "wb") as data_dict_file:
                    ftp.retrbinary(f"RETR {ftp_filename}", data_dict_file.write)

    # Step 2: Check to see if there's a GapExchange file in the parent folder
    #         and if there is, get it.
    ftp.cwd(f"/dbgap/studies/{study_variable}/{study_id}")
    ftp_filelist = ftp.nlst(".")
    for ftp_filename in ftp_filelist:
        if 'GapExchange' in ftp_filename:
            with open(f"{output_dir}/{study_id}/{ftp_filename}", "wb") as data_dict_file:
                ftp.retrbinary(f"RETR {ftp_filename}", data_dict_file.write)
    ftp.quit()
    return True


def main():
    # Delete any existing output dirs so you can ensure all datasets are fresh
    #if os.path.isdir(output_dir):
    #    shutil.rmtree(output_dir)

    # Make new output dir
    os.makedirs(f"{output_dir}/", exist_ok=True)

    # Parse input table and download all valid dbgap datasets to output
    missing_data_dict_studies = {}
    studies = {}

    with open(input_file) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter="\t")
        header = False
        for row in csv_reader:
            if not header:
                # Check to make sure tsv contains column for Study Accession
                if "Study Accession" not in row:
                    # Throw error if expected column is missing
                    raise IOError("Input file must contain 'Study Accession' column")
                header = True
                continue

            # Get platform and make subdir if necessary
            platform = row["Platform"].split(";")
            platform = platform[0] if "BDC" not in platform else "BDC"

            # Add any phs dbgap studies to queue of files to get
            study_id = row["Study Accession"]
            if study_id.startswith("phs") and study_id not in studies:
                studies[study_id] = True
                try:
                    # Try to download to output folder if the study hasn't already been downloaded
                    if not os.path.exists(f"{output_dir}/{platform}/{study_id}"):
                        print(f"Downloading: {study_id}")
                        if not download_dbgap_study(study_id, f"{output_dir}/{platform}"):
                            missing_data_dict_studies[study_id] = True

                except Exception as e:
                    # If anything happens, delete the folder so we don't mistake it for success
                    shutil.rmtree(f"{output_dir}/{platform}/{study_id}")

    # Count the number subdir currently in output_dir as the number of downloaded
    num_downloaded  = len([path for path in os.walk(output_dir) if path[0] != output_dir])

    # Get number of failed for missing data dicts
    num_missing_data_dicts = len(list(missing_data_dict_studies.keys()))

    # Total number of possible unique studies
    num_possible = len(list(studies.keys()))

    # Write out list of datasets with no data dicts
    with open(f"{output_dir}/download_summary.txt", "w") as sum_file:
        sum_file.write(f"Unique dbgap datasets in ncpi table: {num_possible}\n")
        sum_file.write(f"Successfully Downloaded: {num_downloaded}\n")
        sum_file.write(f"Total dbgap datasests missing data dicts: {num_missing_data_dicts}\n")
        sum_file.write(f"Dbgap datasests missing data dicts:\n")
        for item in missing_data_dict_studies:
            sum_file.write(f"{item}\n")

    print(f"Unique dbgap datasets in ncpi table: {num_possible}\n")
    print(f"Successfully Downloaded: {num_downloaded}\n")
    print(f"Total dbgap datasests missing data dicts: {num_missing_data_dicts}\n")


if __name__ == "__main__":
    main()
