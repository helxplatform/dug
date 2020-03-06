from elasticsearch import Elasticsearch
import argparse
import logging
import glob
import json
import requests
import traceback
import os

logger = logging.getLogger (__name__)

class SearchException:
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
    def __init__(self, host="localhost", port=9200, indices=['test']):
        self.indices = indices
        self.crawlspace = "crawl"
        self.es = Elasticsearch([
            {
                'host' : host,
                'port' : port
            }
        ])
        if self.es.ping():
            print('connected to elasticsearch')
            self.init_indices ()
        else:
            raise SearchException (
                message='failed to connect to elasticsearch',
                details=f'connecting to host {host} and port {port}')

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
                result = self.es.indices.create (
                    index=index,
                    body=settings,
                    ignore=400)
                logger.info (f"result creating index {index}: {result}")
            except Exception as e:
                logger.error (f"exception: {e}")
                
    def index_doc (self, index, doc, doc_id):
        self.es.index (
            index=index,
            id=doc_id,
            body=doc)
            
    def search (self, index, query):
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
        with open("phenotypes.json") as stream:
            phenotypes = json.load (stream)
            for phenotype in phenotypes:

                ''' Resolve the phenotype to identifiers. '''
                monarch_query = f"{monarch_endpoint}/{phenotype}"
                accept = [ "EFO", "HP" ]
                response = requests.get (monarch_query).json ()                
                for doc in response.get('response',[]).get ('docs',[]):
                    label = doc['label_eng']
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
    parser.add_argument('--query', help="Query", action="store", dest="query")
    parser.add_argument('--elastic-host', help="Elasticsearch host", action="store", dest="elasticsearch_host")
    parser.add_argument('--elastic-port', help="Elasticsearch port", action="store", dest="elasticsearch_port")
    args = parser.parse_args ()
    
    logging.basicConfig(level=logging.INFO)    
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
        val = search.search (
            index=index,
            query={
                'match': {
                    'name' : {
                        'query' : args.query,
                        'fuzziness' : 1
                    }
                }
            }
        )

        if 'hits' in val:
            for hit in val['hits']['hits']:
                print (hit)
                print (f"{hit['_source']}")
