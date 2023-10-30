#!/bin/sh -x
mkdir -p ${1}
python getConcepts.py "Heart Attack" ${1}
python getConcepts.py "Myocardial Infarction" ${1}
python getConcepts.py "MI" ${1}
python getConcepts.py "Hyperlipidemia" ${1}
python getConcepts.py "High Cholesterol" ${1}
python getConcepts.py "Lipitor" ${1}
python getConcepts.py "Atorvastatin" ${1}
python getConcepts.py "Statin" ${1}
python getConcepts.py "HMGCR" ${1}
python getConcepts.py "Beta-2" ${1}
python getConcepts.py "ADRB2" ${1}
python getConcepts.py "Beta 2 agonist" ${1}
python getConcepts.py "Asthma" ${1}
python getConcepts.py "Joint Pain" ${1}
python getConcepts.py "Acute Pain" ${1}
python getConcepts.py "Morphine" ${1}
python getConcepts.py "Opioid Use" ${1}
python getConcepts.py "Opioid Use Disorder" ${1}
