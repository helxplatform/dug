
# Dug: digging up dark data

Dug applies semantic web and knowledge graph methods to improve the [FAIR](https://www.go-fair.org/fair-principles/)-ness of research data.

As an example, [dbGaP](https://www.ncbi.nlm.nih.gov/gap/) is a rich source of metadata about biomedical knowledge derived from clinical research like the underutilized [TOPMed](https://www.nhlbiwgs.org/) data sets. A key obstacle to leveraging this knowledge is the lack of researcher tools to navigate from a set of concepts of interest towards relevant study variables. In a word, **search**. 

While other approaches to searching this data exist, our focus is semantic search: For us, "relevant" is defined as having a basis in curated, peer reviewed ontologically represented biomedical knowledge. Given a search term, Dug returns results that are related based on connections in ontological biomedical knowledge graphs.

To achieve this, we annotate study metadata with terms from [biomedical ontologies](http://www.obofoundry.org/), contextualize them within a unifying [upper ontology](https://biolink.github.io/biolink-model/) allowing study data to be federated with [larger knowledge graphs](https://researchsoftwareinstitute.github.io/data-translator/), and create a full text search index based on those knowledge graphs.

## The Dug Framework

Dug's **ingest** uses the [Biolink](https://biolink.github.io/biolink-model/) upper ontology to annotate knowledge graphs and structure queries used to drive full text indexing and search. It uses Monarch Initiative APIs to perform named entity recognition on natural language prose to extract ontology identifiers. It also uses Translator normalization services to find preferred identifiers and Biolink types for each extracted identifier. The final step of ingest is to represent the annotated data in a Neo4J graph database.

Dug's **integration** phase uses Translator's Plater and Automat to generate a Reasoner Standard API compliant service and integrates that service into TranQL. This enables queries that span TOPMed, ROBOKOP, and other reasoners.

Dug's **indexing & search** phase query the graph infrastructure and analyze the resulting graphs. These are used to create documents associating natural language terms with annotations and the annotated variables and studies.
![image](https://user-images.githubusercontent.com/306971/94348055-4eb22180-0007-11eb-8093-4e321735ebaf.png)


Dug will then generate Translator knowledge sources for the annotated variables and present them for query via TranQL.

## Knowledge Graphs

Dug's core data structure is the knowledge graph. Here's a query of a COPDGene knowledge graph created by Dug from harmonized TOPMed variables.

![image](https://user-images.githubusercontent.com/306971/77009445-513c0c00-693e-11ea-83ed-722ec896d3e9.png)
**Figure 1**: A Biolink knowledge graph of COPDGene metadata. It shows the relationship between the biological process "Sleep" and a meta variable. The highlighted node is aTOPMed meta variable or harmonized variable. It is in turn associated with variables connected to two studies in the data set. By linking additional ontological terms to the biological process sleep, we will be able to provde progressively more helpful search results rooted in curated biomedical knowledge.

And one more example to illustrate the knowledge model we use to inform the search index:
![image](https://user-images.githubusercontent.com/306971/77230029-b9ba0180-6b67-11ea-9ccf-748955aa1931.png)
**Figure 2**: The TOPMed harmonized variable is highlighted, showing its relationships with the ontology term for Heart Failure and the Heart Failure and with a specific study variable. Several similar disease, harmonized variable, variable, study relationships are also shown.

These graphs are used to create the document's well add to the search index to power full text search.

In phase 1, we use Neo4J to build queries. In subsequent phases, we integrate other semantic services using TranQL.

![image](https://user-images.githubusercontent.com/306971/77681466-bcec2d80-6f6b-11ea-93c5-87eee57d4b66.png)
**Figure 3**: A TranQL knowledge graph query response. Integrating TOPMed harmonized variables as a Translator service called by TranQL allows us to query the federation of Translator ontological connections as a precursor to indexing. This includes chemical, phenotypic, disease, cell type, genetic, and other ontologies from sources like [ROBOKOP](https://researchsoftwareinstitute.github.io/data-translator/apps/robokop) as well as clinical aggregate data from sources like [ICEES](https://researchsoftwareinstitute.github.io/data-translator/apps/icees). The image above shows a query linking cholesterol to "LDL in Blood" a harmonized TOPMed variable. That variable is, in turn, linked to source variables and each of those is linked to its source study.

## Elasticsearch Logic

Elasticsearch contains the indexed knowledge graphs against which we perform full-text queries.  Our query currently supports conditionals (AND, OR, NOT) as well as exact matching on quoted terms.  Because we don't specify an analyzer in our query or when we index documents, we default to the [standard analyzer](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis-standard-analyzer.html), which is recommended for full-text search.  The standard analyzer performs grammar-based tokenization (e.g., splitting up an input string into tokens by several separators including whitespace, commas, hyphens), defined by the [Unicode Standard Annex #29](http://unicode.org/reports/tr29/).

### Example Documents and Query Behavior

Two toy examples of indexed documents, `blood_color` and `blood_shape`, are shown below to demonstrate query behavior.

![image](https://user-images.githubusercontent.com/63300314/85741468-7627e400-b6d0-11ea-849c-7b6da8b630b3.png)

#### Query
The query searches the fields in all indexed documents to return a matching subset of documents.

```
query = {
            'query_string': {
                'query' : query,
                'fuzziness' : fuzziness,
                'fields': ['name', 'description', 'instructions', 'nodes.name', 'nodes.synonyms'],
                'quote_field_suffix': ".exact"
            }
        }
````

#### Tests

| Query|Behavior|
| :--- |  :---- |
| **blood** | This returns both documents (`blood_color` and `blood_shape`). |
| **blood AND magenta**  | This returns only `blood_color`. |
| **magenta AND cerulean** | This returns `blood_color` even though this might be unexpected.  The words 'magenta' and 'cerulean' appear in the same document in the searched fields, even though they appear in different fields, so the document is still returned. |
| **blue AND square** | No documents are returned. |
| **blue and square** | This returns both documents because the 'and' term is treated as just another term instead of an operator because it is not capitalized.  The actual search resolves to **blue OR and OR square** |
| **"round blood"** | No documents are returned. |
| **"blood, round"** | This returns `blood_shape`|
| **"blood round"** | The document `blood_shape` is returned - the standard analyzer performs tokenization based on grammar separators, including commas in this case. |


## Approach

The methodology, from start to finish, reads raw data, annotates it with ontological terms, normalizes those terms, inserts them into a queryable knowledge graph, queries that graph along pre-configured lines, turns the resulting knowledge graphs into documents, and indexes those documents in a full text search engine.

### Link

Link ingests raw dbGaP study metadata and performs semantic annotation by
* Parsing a TOPMed data dictionary XML file to extract variables.
* Using the Monarch SciGraph named entity recognizer to identify ontology terms.
* Using the Translator SRI identifier normalization service to
  * Select a preferred identifier for the entity
  * Determine the BioLink types applying to each entity
* Writing each variable with its annotations as a JSON object to a file.

### Load

* Converts the annotation format written in the steps above to a KGX graph
* Inserts that graph into a Neo4J database.

In phase-1, we query Neo4J to create knowledge graphs. In phase-2 we'll use the Neo4J to create a Translator Knowledge Provider API. That API will be integrated using TranQL with other Translator reasoners like ROBOKOP. This will allow us to build more sophisticated graphs spanning federated ontological knowledge.

### Crawl

* Runs those graph queries and caches knowledge graph responses.

### Index

* Consumes knowledge graphs produced by the crawl.
* Uses connections in the graph to create documents including both full text of variable descriptions and ontology terms.
* Produces a queryable full text index of the variable set.

### Search API

* Presents an OpenAPI compliant REST interface
* Provides a scalable microservice suitable as an Internet endpoint. 

## The Dug Data Development Kit (DDK)

Dug provides a tool chain for the ingest, annotation, knowledge graph representation, query, crawling, indexing, and search of datasets with metadata. The following sections provide an overview of the relevant components.

### Ingest

Data formats for harmonized variables appear to be in flux, hence the multiple approaches. More on this soon.

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
 
### Crawl & Index

| Command        | Description                                                       | Example              |
| -------------- | ----------------------------------------------------------------- | -------------------- |
| bin/dug crawl  | Execute graph queries and accumulate knowledge graphs in response.| bin/dug crawl        |
| bin/dug index  | Analyze crawled knowledge graphs and create search engine indices.| bin/dug index        |
| bin/dug query  | Test the index by querying the search engine from Python.         | bin/dug query {text} |
 
### Search API

Exposing the Elasticsearch interface to the internet is strongly discouraged for security reasons. Instead, we have a REST API. We'll use this as a place to enforce a schema and validate requests so that the search engine's network endpoint is strictly internal.
| Command        | Description           | Example                              |
| -------------- | --------------------- | ------------------------------------ |
| bin/dug api    | Run the REST API.     | bin/dug api [--debug] [--port={int}] |

To call the API endpoint using curl:
| Command             | Description           | Example                   |
| ------------------- | --------------------- | ------------------------- |
| bin/dug query_api   | Call the REST API.    | bin/dug query_api {query} |

## Development

A docker-compose is provided that runs four services:
* Redis
* Neo4J
* Elasticsearch
* The Dug search OpenAPI

This system can be started with the following command:

| Command             | Description                | Example          |
| ------------------- | -------------------------- | ---------------- |
| bin/dug stack       | Runs all services          | bin/dug stack    |

**Developers:** Internal to bin/dug, an environment file is automatically created. That file is in `docker/.env`.
If you are running in development, and are not using a public IP address and hostname, you'll want to create a separate .env file to allow programs to connect to the docker containers as services. This matters if, for example, you want to run bin/test, as the clients in that test need to know how to connect to each of the services they call. Copy the generated docker/.env to docker/.env.dev. Change all hostnames to `localhost`. That should do it. Be sure to keep the generated passwords from the generated .env the same. 

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
**Figure 4**: A command line query using the Dug Search OpenAPI to query the Elasticsearch index for a term.

## Data Formats

Until data formats stabilize, the best approach is to have a look at the raw data [here](https://github.com/helxplatform/dug/tree/master/data).

## Next Steps

These things need attention:
* [x] Develop Kubernetes artifacts to move from development to a public API.
* [ ] Add automated unit tests and a Travis build.
* [x] Apply Plater & Automat to serve the Neo4J as our TOPMed metadata API.
* [x] Demonstrate a TranQL query incorporating this data with ROBOKOP
* [ ] Use TranQL queries to populate Elasticsearch (as shown elsewhere in this repo).
* [ ] Several identifiers returned by the Monarch NLP are not found by the SRI normalizer. The good news is, several of these missing identifiers are quite important (BMI, etc) so once we get them included in normalization, our annotation should be improved.
  * Error logs from data dictionary annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/dd_norm_fail.log).
  * Logs from harmonized variable annotation are [here](https://github.com/helxplatform/dug/blob/master/dug/log/harm_norm_fail.log).
* [x] The input here is a TOPMed DD. Investigate starting the pipeline from harmonized variables.
  * We now have the ability to (roughly) parse harmonized variables from their standard CSV format.
  * Several issues arose around formatting, the need for a study id, and a few other things. 
  * But the overall approach seems feasible.
* [x] Document the crawl, index, and search (API) components of Dug here.

## Future
* [ ] Refine knowledge graph queries and indexing analytics to improve result relevance.
* [ ] Incorporate synonyms and additional NLP approaches.
* [ ] Parallelize steps with Spark.
* [ ] Develop a frictionless KGX interface to Spark.
* [ ] Use Morpheus Cypher for query.


