from elasticsearch import Elasticsearch
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
            
    def search (self, index, query, fuzziness=1):
        query = {
            'match': {
                'name' : {
                    'query' : query,
                    'fuzziness' : fuzziness
                }
            }
        }
        return self.es.search(
            index=index,
            body=json.dumps({ 'query': query }),
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'])

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
    
    parser = argparse.ArgumentParser(description='TranQL-Search')
    parser.add_argument('--clean', help="Clean", default=False, action='store_true')
    parser.add_argument('--crawl', help="Crawl", default=False, action='store_true')
    parser.add_argument('--index', help="Index", default=False, action='store_true')
    parser.add_argument('--index_p1', help="Index - Phase 1 - local graph database rather than Translator query.",
                        default=False, action='store_true')
    parser.add_argument('--query', help="Query", action="store", dest="query")
    parser.add_argument('--elastic-host', help="Elasticsearch host", action="store", dest="elasticsearch_host",
                        default=os.environ.get('ELASTIC_API_HOST', 'localhost'))
    parser.add_argument('--elastic-port', help="Elasticsearch port", action="store", dest="elasticsearch_port",
                        default=os.environ.get('ELASTIC_API_PORT', 9200))
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
