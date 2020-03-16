
# Dug

Dug is a metadata framework enabling ingest, annotation, knowledge graph representation, and full text search. It is conforms to a number of useful semantic standards including [Biolink model](https://biolink.github.io/biolink-model/).
![image](https://user-images.githubusercontent.com/306971/76712938-7426b000-66f3-11ea-94f2-8fc91e58cbea.png)

## Context

Starting with a dbGaP data dictionary for the COPDGene study, we create a Biolink compliant knowledge graph.
[dbGaP](https://www.ncbi.nlm.nih.gov/gap/) is a rich source of metadata about biomedical knowledge derived from clinical research like the underutilized [TOPMed](https://www.nhlbiwgs.org/) data sets. A key obstacle to leveraging this knowledge is the lack of researcher tools to navigate from a set of concepts of interest towards specific study variables related to those interests. In a word, **search**.

While other approaches to searching this data exist, our focus is semantic search: We annotate study metadata with terms from [biomedical ontologies](http://www.obofoundry.org/), contextualize them within a unifying [upper ontology](https://biolink.github.io/biolink-model/) that allows study data to be federated with [larger knowledge graphs](https://researchsoftwareinstitute.github.io/data-translator/), and create a full text search index based on those knowledge graphs.

## Knowledge Graphs

Dug's core construct is the knowledge graph. Here's a query of a knowledge graph created by Dug from COPDGene dbGaP metadata.

![image](https://user-images.githubusercontent.com/306971/76685812-faa49a00-65ec-11ea-9da9-906370b2e1c9.png)
**Figure 1**: A Biolink knowledge graph of COPDGene metadata from dbGaP enables study metadata visualization.

Also, the approach shown here uses study metadata as a starting point, not harmonized variables. But we hope to reuse significant components of the pipeline for processing harmonized variables as well.

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

## The Dug Framework

Dug provides tools for the ingest, annotation, knowledge graph representation, query, crawling, indexing, and search of datasets with metadata. The following sections provide an overview of the relevant tools.

## Metadata Ingest, Annotation, and Knowledge Graph Creation
| Command           | Description                   | Example                  |
| ----------------- | ----------------------------- | ------------------------ |
| bin/dug link  | Use NLP, etc to add ontology identifiers and types. | bin/dug link {input} |
| bin/dug load  | Create a knowledge graph database. | bin/dug load {input} |

There are two example metadata files in the repo.

A COPDGene dbGaP metadata file is at `data/dd.xml`

A harmonized variable metadata CSV is at `data/harmonized_variable_DD.csv`

These can be run with 
```
bin/dug link data/dd.xml
bin/dug load data/dd_tagged.json
```
and
```
bin/dug link data/harmonized_variable_DD.csv
bin/dug load data/harmoinzed_variable_DD_tagged.json
```

## Tools for Crawl & Indexing
| Command        | Description           | Example  |
| -------------- | --------------------- | ----- |
| bin/dug crawl | Execute graph queries and accumulate knowledge graphs in response. | bin/dug crawl |
| bin/dug index | Analyze crawled knowledge graphs and create search engine indices. | bin/dug index |
| bin/dug query | Test the index by querying from the CLI.                           | bin/dug query {text} |
 
## Serving Elasticsearch
Exposing the Elasticsearch interface to the internet is strongly discouraged for security reasons. Instead, we have a REST API. We'll use this as a place to enforce a schema and validate requests so that the search engine's network endpoint is strictly internal.
| Command        | Description           | Example  |
| -------------- | --------------------- | ----- |
| bin/dug api   | Run the REST API. | bin/dug api [--debug] [--port={int}] |


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
![image](https://user-images.githubusercontent.com/306971/76662892-c4680b80-6555-11ea-8a05-731858d08cf3.png)

That's the knowledge graph we'll use to drive a Translator service which will be queried to produce more localized connections as shown in this figure:
![image](https://user-images.githubusercontent.com/306971/76590963-3f351600-64c5-11ea-84d0-f08b7963a1b2.png)

## Next Steps

These things need attention:
* [ ] Several identifiers returned by the Monarch NLP are not found by the SRI normalizer. The good news is, several of these missing identifiers are quite important (BMI, etc) so once we get them included in normalization, our annotation should be improved.
  * Error logs from data dictionary annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/dd_norm_fail.log).
  * Logs from harmonized variable annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/harm_norm_fail.log).
* [x] The input here is a TOPMed DD. Investigate starting the pipeline from harmonized variables.
  * We now have the ability to (roughly) parse harmonized variables from their standard CSV format.
  * Several issues arose around formatting, the need for a study id, and a few other things. 
  * But the overall approach seems feasible.
* [ ] Apply Plater & Automat to serve the Neo4J as our TOPMed metadata API.
* [ ] Demonstrate a TranQL query incorporating this data with ROBOKOP
* [ ] Use TranQL queries to populate Elasticsearch (as shown elsewhere in this repo).

