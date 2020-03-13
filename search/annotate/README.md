
# Overview

[dbGaP](https://www.ncbi.nlm.nih.gov/gap/) is a rich source of metadata about biomedical knowledge derived from clinical research like the underutilized [TOPMed](https://www.nhlbiwgs.org/) data sets. A key obstacle to the utilization of this knowledge is the lack of tools available to researchers to go from a set of concepts of interest towards specific study variables related to those interests. In a word, **search**.

While other approaches to search exist for these data, our focus is semantic search. That is, we aim to annotate the metadata with terms from biomedical ontologies, contextualize them within an upper ontology that allows study data to be federated with larger knowledge graphs, and index a full text search based on on those knowledge graphs.

This prototype 
* Demonstrates how we might annotate dbGaP metadata for a TOPMed study.
* Provides a potential basis for annotating and searching harmonized variables.

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
## Data Formats

The input data dictionary looks like this:
```
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="varreports_v3.xsl"?>
<data_table name="COPDGene_Subject_Phenotypes" dataset_id="pht002239.v4" study_name="Genetic Epidemiology of COPD (COPDGene)" study_id="phs000179.v6" participant_set="2" date_created="2018/04/23">
  <description>Subject ID, died center, age at enrolment, race, ethnic, gender, body weight, body height, BMI, systolic and diastolic blood pressure, measurement of several parameters during 6 minutes work, CT slicer, CT scanner, heart rate, oxygen saturation and therapy, medical history of back pain, cancer, cardio vascular diseases, diabetes, digestive system diseases, eye diseases, general health, musculoskeletal diseases, painful joint type, respiratory tract disease, smoking, and walking limbs, medication history of treatment with beta-agonist, theophylline, inhaled corticosteroid, Oral corticosteroids, ipratropium bromide, and tiotroprium bromide, respiratory disease, St. George's Respiratory Questionnaire, SF-36 Health Survey, spirometry, and VIDA of participants with or without chronic obstructive pulmonary disease and involved in the "Genetic Epidemiology of COPD (COPDGene) Funded by the National Heart, Lung, and Blood Institute" project.</description>
  <variable id="phv00159568.v4.p2" var_name="SUBJECT_ID" calculated_type="string" reported_type="string">
    <description>Dbgap_id</description>
    <total>
      <subject_profile>
        <case_control>
          <case>3692</case>
          <control>4499</control>
        </case_control>
        <sex>
          <male>5524</male>
          <female>4847</female>
        </sex>
      </subject_profile>
      <stats>
        <stat n="10371" nulls="0"/>
      </stats>
    </total>
    <cases>
      <subject_profile>
        <sex>
          <male>2053</male>
          <female>1639</female>
        </sex>
      </subject_profile>
      <stats>
        <stat n="3692" nulls="0"/>
      </stats>
    </cases>
    <controls>
      <subject_profile>
        <sex>
          <male>2355</male>
          <female>2144</female>
        </sex>
      </subject_profile>
      <stats>
        <stat n="4499" nulls="0"/>
      </stats>
    </controls>
  </variable>
...
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

