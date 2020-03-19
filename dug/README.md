
# Dug : digging in dark data

Dug applies semantic web and knowledge graph methods to the improve the [FAIR](https://www.go-fair.org/fair-principles/)-ness of research data.

As an example, [dbGaP](https://www.ncbi.nlm.nih.gov/gap/) is a rich source of metadata about biomedical knowledge derived from clinical research like the underutilized [TOPMed](https://www.nhlbiwgs.org/) data sets. A key obstacle to leveraging this knowledge is the lack of researcher tools to navigate from a set of concepts of interest towards relevant study variables. In a word, **search**. Semantic search is an approach in which "relevant" is defined as having a basis in curated, peer reviewed ontologically represented biomedical knowledge. That is, given a search term, Dug returns results that are related based on connections in ontological biomedical knowledge graphs.

While other approaches to searching this data exist, our focus is semantic search: We annotate study metadata with terms from [biomedical ontologies](http://www.obofoundry.org/), contextualize them within a unifying [upper ontology](https://biolink.github.io/biolink-model/) that allows study data to be federated with [larger knowledge graphs](https://researchsoftwareinstitute.github.io/data-translator/), and create a full text search index based on those knowledge graphs.

## The Dug Framework

Dug uses the [Biolink](https://biolink.github.io/biolink-model/) upper ontology to annotate knowledge graphs and structure queries used to drive full text indexing and search. It uses Monarch Initiative APIs to perform named entity recognition on natural language prose to extract ontology identifiers. It also uses Translator normalization services to find preferred identifiers and Biolink types for each extracted identifier.
![image](https://user-images.githubusercontent.com/306971/76716786-dc7f8c80-6707-11ea-9571-069f27dc5a23.png)

Dug will then generate Translator knowledge sources for the annotated variables and present them for query via TranQL.

Crawl queries TranQL for relevant knowledge graphs. Indexing creates documents based on those graphs and inserts them into a search engine. An OpenAP serves as the query endpoint for a user interface.

## Knowledge Graphs

Dug's core data structure is the knowledge graph. Here's a query of a COPDGene knowledge graph created by Dug from raw data about harmonized TOPMed variables.

![image](https://user-images.githubusercontent.com/306971/77009445-513c0c00-693e-11ea-83ed-722ec896d3e9.png)
**Figure 1**: A Biolink knowledge graph of COPDGene metadata. It shows the relationship between the biological process "Sleep" and a meta variable. The highlighted node is aTOPMed meta variable or harmonized variable. It is in turn associated with variables connected to two studies in the data set. By linking additional ontological terms to the biological process sleep, we will be able to provde progressively more helpful search results rooted in curated biomedical knowledge.

These graphs are used to create the document's well add to the search index to power full text search.

In phase 1, we use Neo4J to build queries. In subsequent phases, we integrate other semantic services using TranQL.

![image](https://user-images.githubusercontent.com/306971/77010772-d9231580-6940-11ea-9a58-00a168ce7b74.png)
**Figure 2**: A TranQL knowledge graph query response. Integrating TOPMed harmonized variables as a Translator service called by TranQL will allow us to make more useful ontological connections as a precursor to indexing.

## Approach

The methodology, from start to finish, reads raw data, annotates it with ontological terms, normalizes those terms, inserts them into a queryable knowledge graph, queries that graph along pre-configured lines, turns the resulting knowledge graphs into documents, and indexes those documents in a full text search engine.

For example, starting with a dbGaP data dictionary for the COPDGene study, we create a Biolink compliant knowledge graph.

Dug 
* Annotates dbGaP metadata for a TOPMed study.
* Provides a potential basis for annotating and searching harmonized variables.

The **link** phase ingests raw dbGaP study metadata and performs semantic annotation by
* Parsing a TOPMed data dictionary XML file to extract variables.
* Using the Monarch SciGraph named entity recognizer to identify ontology terms.
* Using the Translator SRI identifier normalization service to
  * Select a preferred identifier for the entity
  * Determine the BioLink types applying to each entity
* Writing each variable with its annotations as a JSON object to a file.

The **load** phase 
* Converts the annotation format written in the steps above to a KGX graph
* Inserts that graph into a Neo4J database.

In phase-1, we query Neo4J to create knowledge graphs. In phase-2 we'll use the Neo4J to create a Translator Knowledge Provider API. That API will be integrated using TranQL with other Translator reasoners like ROBOKOP. This will allow us to build more sophisticated graphs spanning federated ontological knowledge.

The **crawl** phase
* Runs those graph queries and caches knowledge graph responses.

The **index** phase
* Consumes knowledge graphs produced by the crawl.
* Uses connections in the graph to create documents including both full text of variable descriptions and ontology terms.
* Produces a queryable full text index of the variable set.

The **api** 
* Presents an OpenAPI compliant REST interface
* Protects the Elasticsearch endpoint which is not suitable for exposing 

## The Dug Data Development Kit (DDK)

Dug provides a tool chain for the ingest, annotation, knowledge graph representation, query, crawling, indexing, and search of datasets with metadata. The following sections provide an overview of the relevant components.

## Metadata Ingest, Annotation, and Knowledge Graph Creation
| Command           | Description                                         | Example                  |
| ----------------- | --------------------------------------------------- | ------------------------ |
| bin/dug link      | Use NLP, etc to add ontology identifiers and types. | bin/dug link {input}     |
| bin/dug load      | Create a knowledge graph database.                  | bin/dug load {input}     |

There are three sets of example metadata files in the repo.
* A COPDGene dbGaP metadata file is at `data/dd.xml`
* A harmonized variable metadata CSV is at `data/harmonized_variable_DD.csv`
* Files with names starting with: `data/topmed_*`

This last format seems to be the go-forward TOPMed harmonized variable form.

These can be run with 
```
bin/dug link data/dd.xml
bin/dug load data/dd_tagged.json
```
or 
```
bin/dug link data/harmonized_variable_DD.csv
bin/dug load data/harmoinzed_variable_DD_tagged.json
```
or
```
bin/dug link data/topmed_variables_v1.0.csv [--index x]
```
The first two formats will likely go away.
The last format
* Consists of two sets of files following that naming convention.
* Combines the link and load phases into link.
* Optionally allows the --index <arg> flag. This will run graph queries and index data in Elasticsearch.
 
## Tools for Crawl & Indexing
| Command        | Description                                                       | Example              |
| -------------- | ----------------------------------------------------------------- | -------------------- |
| bin/dug crawl  | Execute graph queries and accumulate knowledge graphs in response.| bin/dug crawl        |
| bin/dug index  | Analyze crawled knowledge graphs and create search engine indices.| bin/dug index        |
| bin/dug query  | Test the index by querying the search engine from Python.         | bin/dug query {text} |
 
## Serving Elasticsearch
Exposing the Elasticsearch interface to the internet is strongly discouraged for security reasons. Instead, we have a REST API. We'll use this as a place to enforce a schema and validate requests so that the search engine's network endpoint is strictly internal.
| Command        | Description           | Example                              |
| -------------- | --------------------- | ------------------------------------ |
| bin/dug api    | Run the REST API.     | bin/dug api [--debug] [--port={int}] |

To call the API endpoint using curl:
| Command             | Description           | Example                   |
| ------------------- | --------------------- | ------------------------- |
| bin/dug query_api   | Call the REST API.    | bin/dug query_api <query> |

## Development

A docker-compose is provided that runs four services:
* Redis
* Neo4J
* Elasticsearch
* The Dug search OpenAPI

| Command             | Description                | Example          |
| ------------------- | -------------------------- | ---------------- |
| bin/dug dev init    | Generate docker/.env config| bin/dug dev init |
| bin/dug stack       | Runs all services          | bin/dug stack    |
| bin/dug dev conf    | Configure environment vars | bin/dug dev conf |

* Init must be run exactly once before starting the docker-compose the first time.
* Delete docker/db/* and re-run to reset everything.
* Conf must be run before any clients that connect to the service to set up environment variables.

## Testing

Dug's automated functional tests:
* Delete the test index
* Execute the link and load phases for the dbGaP data dictionary and harmonized variables.
* Execute the crawl and index phases.
* Execute a number of searches over the generated search index.

| Command             | Description                    | Example      |
| ------------------- | ------------------------------ | ------------ |
| bin/dug test        | Run automated functional tests | bin/dug test |

Once the test is complete, a command line search shows the contents of the index:
![image](https://user-images.githubusercontent.com/306971/77009780-e939f580-693e-11ea-8a02-ca2fd59d4366.png)

## Data Formats

Until data formats stabilize, the best approach is to have a look at the raw data [here](https://github.com/helxplatform/dug/tree/master/data).

## Next Steps

These things need attention:
* [ ] Develop Kubernetes artifacts to move from development to a public API.
* [ ] Add automated unit tests and a Travis build.
* [ ] Apply Plater & Automat to serve the Neo4J as our TOPMed metadata API.
* [ ] Demonstrate a TranQL query incorporating this data with ROBOKOP
* [ ] Use TranQL queries to populate Elasticsearch (as shown elsewhere in this repo).
* [ ] Several identifiers returned by the Monarch NLP are not found by the SRI normalizer. The good news is, several of these missing identifiers are quite important (BMI, etc) so once we get them included in normalization, our annotation should be improved.
  * Error logs from data dictionary annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/dd_norm_fail.log).
  * Logs from harmonized variable annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/harm_norm_fail.log).
* [x] The input here is a TOPMed DD. Investigate starting the pipeline from harmonized variables.
  * We now have the ability to (roughly) parse harmonized variables from their standard CSV format.
  * Several issues arose around formatting, the need for a study id, and a few other things. 
  * But the overall approach seems feasible.
* [x] Document the crawl, index, and search (API) components of Dug here.

