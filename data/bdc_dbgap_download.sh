#!/bin/bash
#
# Download the data dictionaries from dbGaP as listed in bdc_dbgap_ids.csv
# into the bdc_dbgap/ directory.
#

CSV_FILE=bdc_dbgap_ids.csv
OUTPUT_DIR=bdc_dbgap_data_dicts
SCRIPT=../bin/get_dbgap_data_dicts.py
PYTHON=${PYTHON:-python3}

mkdir -p $OUTPUT_DIR
$PYTHON $SCRIPT $CSV_FILE --format CSV --field Accession --outdir $OUTPUT_DIR --skip phs000571.v6.p2
