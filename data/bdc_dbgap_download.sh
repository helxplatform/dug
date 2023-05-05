#!/bin/bash
#
# Download the data dictionaries from dbGaP as listed in bdc_dbgap_ids.csv
# into the bdc_dbgap/ directory.
#

CSV_FILE=bdc_dbgap_ids.csv
OUTPUT_DIR=bdc_dbgap_data_dicts
SCRIPT=../bin/get_dbgap_data_dicts.py

mkdir -p $OUTPUT_DIR
python $SCRIPT $CSV_FILE --format CSV --field Accession --outdir $OUTPUT_DIR
