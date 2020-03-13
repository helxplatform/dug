
# Overview

The **annotator** ingests raw dbGaP study metadata and performs semantic annotation by
* Parsing a TOPMed data dictionary XML file to extract variables.
* Using the Monarch SciGraph named entity recognizer to identify ontology terms.
* Using the Translator SRI identifier normalization service to
  * Select a preferred identifier for the entity
  * Determine the BioLink types applying to each entity
* Writing each variable with its annotations as a JSON object to a file.

The **loader** 
* Converts the annotation format written in the steps above to a KGX graph
* Inserts that graph into a Neo4J database.

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
Install Translator KGX:
```
git clone https://github.com/NCATS-Tangerine/kgx.git
```
Annotate a data dictionary via Monarch NLP 
```
PYTHONPATH=$PWD:$PWD/kgx python -m search.annotate.annotator --annotate dd.xml
```
Load the resulting graph into Neo4J
```
PYTHONPATH=$PWD:$PWD/kgx python -m search.annotate.annotator --load dd_tagged.json
```

An annotated variable from the *annotate* step looks like this:
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
The load step gives us one study object, the hub in this figure, connected to many study variables, each connected to ontology terms to which those variables are related.
![image](https://user-images.githubusercontent.com/306971/76589696-4b1ed900-64c1-11ea-9a8d-145dbb6a83be.png)

That's the knowledge graph we'll use to drive a Translator service which will be queried to produce more localized connections as shown in this figure:
![image](https://user-images.githubusercontent.com/306971/76590963-3f351600-64c5-11ea-84d0-f08b7963a1b2.png)


## Next Steps

These things need attention:
* [ ] Several identifiers returned by the Monarch NLP are not found by the SRI normalizer. eg:
 ```
 error normalizing curie: BFO:0000029
ERROR: curie:BFO:0000029 returned preferred id: {}
error normalizing curie: SO:0000408
ERROR: curie:SO:0000408 returned preferred id: {}
error normalizing curie: IAO:0000230
ERROR: curie:IAO:0000230 returned preferred id: {}
error normalizing curie: AQTLTrait:3239
ERROR: curie:AQTLTrait:3239 returned preferred id: {}
error normalizing curie: OBO:OGMS_0000031
ERROR: curie:OBO:OGMS_0000031 returned preferred id: {}
error normalizing curie: AQTLTrait:1438
ERROR: curie:AQTLTrait:1438 returned preferred id: {}
error normalizing curie: dc:subject
ERROR: curie:dc:subject returned preferred id: {}
error normalizing curie: NCBIGene:22819
...
 ```
* [ ] The input here is a TOPMed DD. Investigate starting the pipeline from harmonized variables.
* [ ] Apply Plater & Automat to serve the Neo4J as our TOPMed metadata API.
* [ ] Demonstrate a TranQL query incorporating this data with ROBOKOP
* [ ] Use TranQL queries to populate Elasticsearch (as shown elsewhere in this repo).

