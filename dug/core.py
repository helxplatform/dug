from elasticsearch import Elasticsearch
from dug.annotate import TOPMedStudyAnnotator
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
        query = {
            'multi_match': {
                'query' : query,
                'fuzziness' : fuzziness,
                'fields': ['name', 'description', 'instructions', 'nodes.name', 'nodes.synonyms']
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

    def tagged_crawl (self, tags, variables, index, min_score=0.2):
        tranql_endpoint = "https://tranql.renci.org/tranql/query?dynamic_id_resolution=true&asynchronous=false"
        headers = {
            "accept" : "application/json",
            "Content-Type" : "text/plain"
        }

        self.make_crawlspace ()
        for tag in tags:
            # Get subset of variables for this tag
            tagged_variables = [variable for variable in variables if int(variable["tag_pk"]) == int(tag["pk"])]

            logging.debug(f"Doing variables with tag: {tag['title']}")
            for identifier in tag["identifiers"]:
                logging.debug(f"Doing id: {identifier}")
                ''' Resolve the phenotype to identifiers. '''

                # Boolean switch for whether a knowledge graph has been returned for the current identifier
                # If no knowledge graphs are returned by TranQL just put a normal record with no nodes/KG
                has_kg = False

                queries = {"pheno": f"select phenotypic_feature->disease from '/graph/gamma/quick' where phenotypic_feature='{identifier}'",
                           "disease": f"select d1:disease_or_phenotypic_feature->d2:disease_or_phenotypic_feature from '/graph/gamma/quick' where d1='{identifier}'",
                           "anat": f"select d1:disease-[subclass_of]->d2:disease->anatomical_entity from '/graph/gamma/quick' where d1='{identifier}'"}

                # Loop through each query and try to add the answers to the search index
                for query_name, query in queries.items():

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

                    # Case: Skip if empty KG
                    if not len(response["knowledge_graph"]["nodes"]):
                        logging.debug(f"Did not find a knowledge graph for {query}")
                        continue

                    # Dump out to file if there's a knowledge graph
                    with open(filename, 'w') as stream:
                        json.dump(response, stream, indent=2)

                    # Set boolean flag to true so we know not to put in dummy record after all queries are run
                    has_kg = True

                    # Get nodes in knowledge graph hashed by ids for easy lookup
                    nodes = {node["id"]: node for node in response.get('knowledge_graph',{}).get('nodes',[])}
                    answers = response.get('knowledge_map', {})

                    # Create ES entries for each variable for each answer
                    for answer in answers:
                        # Filter out answers that fall below a minimum score
                        if answer["score"] < min_score:
                            continue
                        logger.debug(f"Answer: {answer}")

                        answer_nodes = []
                        for id, node_bindings in answer["node_bindings"].items():
                            answer_nodes += [nodes[answer_node] for answer_node in node_bindings]
                        answer_node_ids = [answer_node["id"] for answer_node in answer_nodes]

                        # Add each variable to ES and add information for nodes and the knowledge graph returned from TranQL
                        for variable in tagged_variables:
                            doc = {"name": tag["identifiers"][identifier]["label"],
                                   "id": identifier,
                                    "var": variable["variable_id"].replace("TOPMED.VAR:", ""),
                                    "tag": variable["tag_pk"],
                                    "description": tag["description"],
                                    "instructions": tag["instructions"],
                                    "study": variable["study_id"].replace("TOPMED.STUDY:", ""),
                                    "study_name": variable["study_name"],
                                    "nodes": answer_nodes,
                                    "knowledge_map": answer}

                            logger.debug(f"{json.dumps(doc, indent=2)}")
                            unique_doc_id = f"{doc['id']}_{doc['study']}_{doc['var']}_{'_'.join(answer_node_ids)}_{query_name}"

                            """ Index the document. """
                            self.index_doc(
                                index=index,
                                doc=doc,
                                doc_id=unique_doc_id)

                # Write textual entries for variables that didn't return KG for any of their identifiers
                # Makes sure we don't just drop things that don't return answers from TranQL
                if not has_kg:
                    for variable in tagged_variables:
                        doc = {"name": tag["identifiers"][identifier]["label"],
                                "id": identifier,
                                "var": variable["variable_id"].replace("TOPMED.VAR:", ""),
                                "tag": variable["tag_pk"],
                                "description": tag["description"],
                                "instructions": tag["instructions"],
                                "study": variable["study_id"].replace("TOPMED.STUDY:", ""),
                                "study_name": variable["study_name"],
                                "nodes": [],
                                "knowledge_map": {}}

                        logger.debug(f"No answer returned from TranQL:\n{json.dumps(doc, indent=2)}")
                        unique_doc_id = f"{doc['id']}_{doc['study']}_{doc['var']}"

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
        search.tagged_crawl(tags, variables, index)

