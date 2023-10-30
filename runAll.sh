#!/bin/sh -x
# $1 is the basedir in which to look for results.  $2 is the outputDir
mkdir -p ${2}
python combineResults.py "Acute_Pain-NCIT:C27003" ${1} ${2}
python combineResults.py "Asthma-MONDO:0004979" ${1} ${2}
python combineResults.py "Atorvastatin-PUBCHEM.COMPOUND:60823" ${1} ${2}
python combineResults.py "HMGCR-UMLS:C0020375" ${1} ${2}
python combineResults.py "Heart_Attack-MONDO:0005068" ${1} ${2}
python combineResults.py "High_Cholesterol-HP:0003124" ${1} ${2}
python combineResults.py "Hyperlipidemia-MONDO:0021187" ${1} ${2}
python combineResults.py "Joint_Pain-HP:0002829" ${1} ${2}
python combineResults.py "Lipitor-PUBCHEM.COMPOUND:60823" ${1} ${2}
python combineResults.py "MI-MONDO:0005068" ${1} ${2}
python combineResults.py "Morphine-PUBCHEM.COMPOUND:5288826" ${1} ${2}
python combineResults.py "Myocardial_Infarction-MONDO:0005068" ${1} ${2}
python combineResults.py "Opioid_Use-MONDO:0005530" ${1} ${2}
python combineResults.py "Opioid_Use_Disorder-MONDO:0005530" ${1} ${2}
python combineResults.py "Statin-CHEBI:87631" ${1} ${2}
