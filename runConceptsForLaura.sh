#!/bin/sh -x
mkdir -p ${1}
python getConcepts.py "Codeine" ${1}
python getConcepts.py "Modafinil" ${1}
python getConcepts.py "MCI" ${1}
