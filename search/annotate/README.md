
# Overview

The annotator ingests raw dbGaP study metadata and performs semantic annotation by
* Using the Monarch SciGraph named entity recognizer to identify ontology terms.
* Using the Translator SRI identifier normalization service to 
  * Select a preferred identifier for the entity
  * Determine the BioLink types applying to each entity
* Writing each variable with its annotations as a JSON object to a file.

## Install

In the repo root:

Get a TOPMed study data dictionary:
```
curl ftp://ftp.ncbi.nlm.nih.gov/dbgap/studies/phs000179/phs000179.v6.p2/pheno_variable_summaries/phs000179.v6.pht002239.v4.COPDGene_Subject_Phenotypes.data_dict.xml -o dd.xml
```
Install Python dependencies:
```
pip install -r requirementst.txt
```
Run
```
python search/annotate/annotator.py dd.xml
```

A field from the output looks like this:
```
  {
    "study_id": "phs000179.v6",
    "variable_id": "phv00169306.v3",
    "variable": "ExclusionaryDisease",
    "description": "other primary disease so subject excluded from copd disease analysis [ild, bronchiectasis]",
    "identifiers": {
      "MONDO:0000001": {
        "label": "disease or disorder",
        "equivalent_identifiers": [
          "MONDO:0000001",
          "DOID:4",
          "ORPHANET:377788",
          "UMLS:C0012634",
          "MESH:D004194",
          "NCIT:C2991",
          "SNOMEDCT:64572001"
        ],
        "type": [
          "disease",
          "named_thing",
          "biological_entity",
          "disease_or_phenotypic_feature"
        ]
      },
      "HP:0040285": {
        "label": "",
        "equivalent_identifiers": [
          "HP:0040285",
          "UMLS:C0332196",
          "SNOMEDCT:77765009"
        ],
        "type": [
          "phenotypic_feature",
          "disease_or_phenotypic_feature",
          "biological_entity",
          "named_thing"
        ]
      },
      "MONDO:0011751": {
        "label": "COPD, severe early onset",
        "equivalent_identifiers": [
          "MONDO:0011751",
          "OMIM:606963"
        ],
        "type": [
          "disease",
          "disease_or_phenotypic_feature",
          "biological_entity",
          "named_thing"
        ]
      }
    }
  },
```
![image](https://user-images.githubusercontent.com/306971/76590963-3f351600-64c5-11ea-84d0-f08b7963a1b2.png)

![image](https://user-images.githubusercontent.com/306971/76589696-4b1ed900-64c1-11ea-9a8d-145dbb6a83be.png)
