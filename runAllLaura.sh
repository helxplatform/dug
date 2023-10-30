#!/bin/sh -x
# $1 is the basedir in which to look for results.  $2 is the outputDir
mkdir -p ${2}
python combineResults.py "Codeine-PUBCHEM.COMPOUND:5284371" ${1} ${2}
python combineResults.py "MCI-UMLS:C4277733" ${1} ${2}
python combineResults.py "Modafinil-PUBCHEM.COMPOUND:4236" ${1} ${2}
