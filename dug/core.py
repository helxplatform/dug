from elasticsearch import Elasticsearch
from dug.annotate import TOPMedStudyAnnotator
import dug.tranql as tql
import argparse
import logging
import glob
import json
import requests
import sys
import traceback
import os

logger = logging.getLogger (__name__)

logging.getLogger("elasticsearch").setLevel(logging.WARNING)

class SearchException (Exception):
    def __init__(self, message, details):
        self.message = message
        self.details = details

class Search:
    """ Search -
    1. Lexical fuzziness; (a) misspellings - a function of elastic.
    2. Fuzzy ontologically;
       (a) expand based on core queries
         * phenotype->study
         * phenotype->disease->study
         * disease->study
         * disease->phenotype->study
    """
    def __init__(self, host=os.environ.get('ELASTIC_API_HOST'), port=9200, indices=['test']):
        logger.debug (f"Connecting to elasticsearch host: {host} at port: {port}")
        self.indices = indices
        self.crawlspace = "crawl"
        self.host = os.environ.get ('ELASTIC_API_HOST', 'localhost')
        self.username = os.environ.get ('ELASTIC_USERNAME', 'elastic')
        self.password = os.environ.get ('ELASTIC_PASSWORD', 'changeme')
        self.hosts = [
            {
                'host' : self.host,
                'port' : port
            }
        ]
        logger.debug (f"Authenticating as user {self.username} to host:{self.hosts}")
        self.es = Elasticsearch (hosts=self.hosts,
                                 http_auth=(self.username, self.password))

        if self.es.ping():
            logger.info ('connected to elasticsearch')
            self.init_indices ()
        else:
            print (f"Unable to connect to elasticsearch at {host}:{port}")
            logger.error (f"Unable to connect to elasticsearch at {host}:{port}")
            raise SearchException (
                message='failed to connect to elasticsearch',
                details=f"connecting to host {host} and port {port}")

    def clean (self):
        self.es.indices.delete ("*")

    def init_indices (self):
        settings = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "name": {
                        "type": "text"
                    },
                    "type": {
                        "type": "text"
                    }
                }
            }
        }
        logger.info (f"creating indices: {self.indices}")
        for index in self.indices:
            try:
                if self.es.indices.exists(index=index):
                    logger.info (f"Ignoring index {index} which already exists.")
                else:
                    result = self.es.indices.create (
                        index=index,
                        body=settings,
                        ignore=400)
                    logger.info (f"result created index {index}: {result}")
            except Exception as e:
                logger.error (f"exception: {e}")
                raise e

    def index_doc (self, index, doc, doc_id):
        self.es.index (
            index=index,
            id=doc_id,
            body=doc)

    def search (self, index, query, offset=0, size=None, fuzziness=1):
        """
        Query type is now 'query_string'.
        query searches multiple fields
        if search terms are surrounded in quotes, looks for exact matches in any of the fields
        AND/OR operators are natively supported by elasticesarch queries
        """
        query = {
            'query_string': {
                'query' : query,
                'fuzziness' : fuzziness,
                'fields': ['name', 'description', 'instructions', 'knowledge_graph.knowledge_graph.nodes.name', 'knowledge_graph.knowledge_graph.nodes.synonyms'],
                'quote_field_suffix': ".exact"
            }
            
        }
        body = json.dumps({'query': query})
        total_items = self.es.count(body=body)
        search_results = self.es.search(
            index=index,
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results

    def make_crawlspace (self):
        if not os.path.exists (self.crawlspace):
            try:
                os.makedirs (self.crawlspace)
            except Exception as e:
                print (f"-----------> {e}")
                traceback.print_exc ()

    def crawl (self):
        monarch_endpoint = "https://monarchinitiative.org/searchapi"
        tranql_endpoint = "https://tranql.renci.org/tranql/query?dynamic_id_resolution=true&asynchronous=false"
        headers = {
            "accept" : "application/json",
            "Content-Type" : "text/plain"
        }
        self.make_crawlspace ()
        phenotype_list = os.path.join (os.path.dirname (__file__), "conf", "phenotypes.json")
        with open(phenotype_list) as stream:
            phenotypes = json.load (stream)
            for phenotype in phenotypes:

                ''' Resolve the phenotype to identifiers. '''
                monarch_query = f"{monarch_endpoint}/{phenotype}"
                monarch_query = f"https://api.monarchinitiative.org/api/search/entity/{phenotype}?start=0&rows=25&highlight_class=hilite&boost_q=category%3Agenotype%5E-10&boost_q=category%3Avariant%5E-35&boost_q=category%3Apublication%5E-10&prefix=-OMIA&min_match=67%25&category=gene&category=variant&category=genotype&category=phenotype&category=disease&category=goterm&category=pathway&category=anatomy&category=substance&category=individual&category=case&category=publication&category=model&category=anatomical+entity"
                accept = [ "EFO", "HP" ]
                logger.debug (f"monarch query: {monarch_query}")
                #response = requests.get (monarch_query)
                #logger.debug (f"   {response.text}")
                #response = response.json ()
                response = requests.get (monarch_query).json ()
                for doc in response.get('docs',[]): #.get ('docs',[]):
                    label = doc.get('label_eng',['N/A'])[0]
                    identifier = doc['id']

                    if not any(map(lambda v: identifier.startswith(v), accept)):
                        continue

                    filename = f"{self.crawlspace}/{identifier}.json"
                    if os.path.exists (filename):
                        logger.info (f"identifier {identifier} is already crawled.")
                        continue

                    query = f"select phenotypic_feature->disease from '/graph/gamma/quick' where phenotypic_feature='{identifier}'"
                    logger.info (query)
                    response = requests.post (
                        url = tranql_endpoint,
                        headers = headers,
                        data = query).json ()
                    with open(filename, 'w') as stream:
                        json.dump (response, stream, indent=2)

    def tagged_crawl (self, tags, variables, index, min_score=0.2, include_node_keys=["id", "name", "synonyms"], include_edge_keys=[]):
        tranql_endpoint = "https://tranql.renci.org/tranql/query?dynamic_id_resolution=true&asynchronous=false"
        headers = {
            "accept" : "application/json",
            "Content-Type" : "text/plain"
        }

        self.make_crawlspace ()
        for tag in tags:
            # Get subset of variables for this tag
            tagged_variables = [variable for variable in variables if int(variable["tag_pk"]) == int(tag["pk"])]
            tag_indexed = False

            logging.debug(f"Doing variables with tag: {tag['title']}")
            for identifier in tag["identifiers"]:

                logging.debug(f"Doing id: {identifier}")
                ''' Resolve the phenotype to identifiers. '''

                # Boolean switch for whether a knowledge graph has been returned for the current identifier
                # If no knowledge graphs are returned by TranQL just put a normal record with no nodes/KG
                identifier_indexed = False

                queries = {"disease": f"select d1:disease_or_phenotypic_feature->d2:disease_or_phenotypic_feature from '/graph/gamma/quick' where d1='{identifier}'",
                           "anat": f"select d1:disease-[subclass_of]->d2:disease->anatomical_entity from '/graph/gamma/quick' where d1='{identifier}'",
                           "chem_to_disease": f"select d1:chemical_substance->disease_or_phenotypic_feature from '/graph/gamma/quick' where d1='{identifier}'",
                           "chem_to_disease_disease": f"select d1:chemical_substance->disease_or_phenotypic_feature->d2:disease_or_phenotypic_feature from '/graph/gamma/quick' where d1='{identifier}'",
                           "chem_to_gene_to_disease": f"select d1:chemical_substance->gene->disease from '/graph/gamma/quick' where d1='{identifier}'",
                           "phen_to_anat": f"select d1:phenotypic_feature->anatomical_entity from '/graph/gamma/quick' where d1='{identifier}'"}

                # Loop through each query and try to add the answers to the search index
                for query_name, query in queries.items():

                    # Skip identifiers that didn't normalize
                    if not tag["identifiers"][identifier]["label"]:
                        logging.debug(f"Skipping non-normalized identifier: {identifier}")
                        continue

                    # Skip query if a file exists in the crawlspace exists already
                    filename = f"{self.crawlspace}/{identifier}_{query_name}.json"
                    if os.path.exists(filename):
                        logger.info(f"identifier {identifier} is already crawled.")
                        continue

                    # Submit query to TranQL
                    logger.info (query)
                    response = requests.post(
                        url = tranql_endpoint,
                        headers = headers,
                        data = query).json ()

                    print(response)

                    # Case: Skip if empty KG
                    if not len(response["knowledge_graph"]["nodes"]):
                        logging.debug(f"Did not find a knowledge graph for {query}")
                        continue

                    # Dump out to file if there's a knowledge graph
                    with open(filename, 'w') as stream:
                        json.dump(response, stream, indent=2)

                    # Get nodes in knowledge graph hashed by ids for easy lookup
                    kg = tql.QueryKG(response)

                    # Create ES entries for each variable for each answer
                    for answer in kg.answers:

                        # Filter out answers that fall below a minimum score
                        # TEMPORARY: Robokop stopped including scores temporarily so ignore these for time being
                        if "score" in answer and answer["score"] < min_score:
                            continue
                        logger.debug(f"Answer: {answer}")

                        # Get subgraph containing only information for this answer
                        try:
                            # Temporarily surround in try/except because sometimes the answer graphs
                            # contain invalid references to edges/nodes
                            # This will be fixed in Robokop but for now just silently warn if answer is invalid
                            answer_kg = kg.get_answer_subgraph(answer,
                                                               include_node_keys=include_node_keys,
                                                               include_edge_keys=include_edge_keys)

                            # Get list of nodes for making a unique ID for elastic search
                            answer_node_ids = list(answer_kg.nodes.keys())

                        except tql.MissingNodeReferenceError:
                            # TEMPORARY: Skip answers that have invalid node references
                            # Need this to be fixed in Robokop
                            logger.warning("Skipping answer due to presence of non-preferred id! "
                                           "See err msg for details.")
                            continue
                        except tql.MissingEdgeReferenceError:
                            # TEMPORARY: Skip answers that have invalid edge references
                            # Need this to be fixed in Robokop
                            logger.warning("Skipping answer due to presence of invalid edge reference! "
                                           "See err msg for details.")
                            continue

                        # Add each variable to ES with info specific to current answer
                        self.index_tagged_variables(tag,
                                                    tagged_variables,
                                                    index,
                                                    identifier=identifier,
                                                    knowledge_graph=answer_kg.kg,
                                                    query_name=query_name,
                                                    answer_node_ids=answer_node_ids)

                        # Set boolean flag that at least one answer has been added to elastic for an identifier
                        # Now we know we don't need to write a dummy record for this identifier
                        identifier_indexed = True
                        tag_indexed = True

                # Write textual entries for identifiers that didn't return KG from TranQL
                # Ensures we don't lose the ability to search on tag identifier labels returned from Monarch
                if not identifier_indexed and tag["identifiers"][identifier]["label"]:
                    self.index_tagged_variables(tag,
                                                tagged_variables,
                                                index,
                                                identifier=identifier)

                    # Indicate that tag has been indexed at least once
                    # Now we know we don't need to write a dummy record for this tag
                    tag_indexed = True

            # Handle the exceptional case where a tag doesn't actually have any identifiers
            # (i.e. Monarch didn't know what it was)
            # We need to add records so we can at least still search on the tag's generic name/description
            if not tag_indexed:
                self.index_tagged_variables(tag,
                                            tagged_variables,
                                            index)
                        
    def index_tagged_variables(self, tag, variables, index, identifier="", knowledge_graph={}, query_name="", answer_node_ids=[]):
        # Internal class helper method for writing a list of tagged variables to Elastic Search

        # Use identifier label as name if identifier exists
        # Some tags may not have identifiers (e.g. when Monarch fails to return something) so just use empty string
        name = tag["identifiers"][identifier]["label"] if identifier else ""

        for variable in variables:
            doc = {"name": name,
                   "id": identifier,
                   "var": variable["variable_id"].replace("TOPMED.VAR:", ""),
                   "tag": variable["tag_pk"],
                   "description": tag["description"],
                   "instructions": tag["instructions"],
                   "study": variable["study_id"].replace("TOPMED.STUDY:", ""),
                   "study_name": variable["study_name"],
                   "knowledge_graph": knowledge_graph}

            # Create unique ID
            if answer_node_ids and query_name:
                # Case: Variable is created from KG query and needs query and answer nodes to be unique
                logger.debug("Indexing TranQL query answer...")
                unique_doc_id = f"{doc['id']}_{doc['study']}_{doc['var']}_{'_'.join(answer_node_ids)}_{query_name}"
            elif doc['id']:
                logger.debug("Indexing identifier that didn't return anything from TranQL")
                # Case: Variable is created from one of a tag's identifiers and identifier can be used as unique
                unique_doc_id = f"{doc['id']}_{doc['study']}_{doc['var']}"
            else:
                # Case: Variable doesn't have any identifiers (monarch failed)
                # The study name/variable name will be fine for unique
                logger.debug("Indexing generic tagged variable...")
                unique_doc_id = f"{doc['study']}_{doc['var']}"

            logger.debug(f"ElasticSearch ID: {unique_doc_id}\n{json.dumps(doc, indent=2)}")

            """ Index the document. """
            self.index_doc(
                index=index,
                doc=doc,
                doc_id=unique_doc_id)

    def index (self, index):
        self.make_crawlspace ()
        files = glob.glob (f"{self.crawlspace}/*.json")
        for f in files:
            print (f"index {f}")
            with open (f, 'r') as stream:
                kg = None
                try:
                    kg = json.load (stream)
                except Exception as e:
                    logger.error (f"Failed reading: {f}")
                    logger.error (e)
                if not kg:
                    continue
                #print ([ x for x in kg ])
                nodes = kg.get('knowledge_graph',{}).get('nodes',[])
                print (f"kg: {nodes}")
                doc = {
                    'diseases' : []
                }

                root_id = None
                for node in nodes:
                    identifier = node['id']
                    if identifier.startswith ('HP'):
                        doc['id'] = identifier
                        root_id = identifier
                        doc['name'] = node['synonyms']
                    else:
                        doc['diseases'].append (identifier)

                print (f"{json.dumps(doc, indent=2)}")
                search.index_doc (
                    index=index,
                    doc=doc,
                    doc_id=root_id)

if __name__ == '__main__':

    db_url_default = "http://" + os.environ.get('NEO4J_HOST', 'localhost') + ":" + os.environ.get('NEO4J_PORT',
                                                                                                  '7474') + "/db/data"
    
    parser = argparse.ArgumentParser(description='TranQL-Search')
    parser.add_argument('--clean', help="Clean", default=False, action='store_true')
    parser.add_argument('--crawl', help="Crawl", default=False, action='store_true')
    parser.add_argument('--index', help="Index", default=False, action='store_true')
    parser.add_argument('--tagged-crawl', help='Crawl tagged variables', dest="tagged")
    parser.add_argument('--min-tranql-score', help='Minimum score to consider an answer from TranQL',
                        dest="min_tranql_score",
                        default=0.2, type=float)
    parser.add_argument('--index_p1', help="Index - Phase 1 - local graph database rather than Translator query.",
                        default=False, action='store_true')
    parser.add_argument('--query', help="Query", action="store", dest="query")
    parser.add_argument('--elastic-host', help="Elasticsearch host", action="store", dest="elasticsearch_host",
                        default=os.environ.get('ELASTIC_API_HOST', 'localhost'))
    parser.add_argument('--elastic-port', help="Elasticsearch port", action="store", dest="elasticsearch_port",
                        default=os.environ.get('ELASTIC_API_PORT', 9200))

    parser.add_argument('--db-url', help='database url', default=db_url_default)
    parser.add_argument('--db-username', help='database username', default='neo4j')
    parser.add_argument('--db-password', help='database password', default=os.environ['NEO4J_PASSWORD'])
    args = parser.parse_args ()

    logging.basicConfig(level=logging.DEBUG)
    index = "test"
    search = Search (host=args.elasticsearch_host,
                     port=args.elasticsearch_port,
                     indices=[index])

    if args.clean:
        search.clean ()
    if args.crawl:
        search.crawl ()
    if args.index:
        search.index (index)
        search.index_doc (
            index=index,
            doc= {
                "name" : "fred",
                "type" : "phenotypic_feature"
            },
            doc_id=1)
    elif args.query:
        val = search.search (index=index, query=args.query)
        if 'hits' in val:
            for hit in val['hits']['hits']:
                print (hit)
                print (f"{hit['_source']}")

    elif args.tagged:

        config = {
            'annotator': "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
            'normalizer': "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
            'password': os.environ['NEO4J_PASSWORD'],
            'username': 'neo4j',
            'db_url': db_url_default,
            'redis_host': os.environ.get('REDIS_HOST', 'localhost'),
            'redis_port': os.environ.get('REDIS_PORT', 6379),
            'redis_password': os.environ.get('REDIS_PASSWORD', ''),
        }

        config['username'] = args.db_username
        config['password'] = args.db_password
        config['db_url'] = args.db_url

        # Create annotator object
        annotator = TOPMedStudyAnnotator(config=config)

        # Annotate tagged variables
        variables, tags = annotator.load_tagged_variables(args.tagged)
        tags = annotator.annotate(tags)

        # Append tag info to variables
        search.tagged_crawl(tags, variables, index, min_score=args.min_tranql_score)

