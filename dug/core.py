from elasticsearch import Elasticsearch
from dug.annotate import TOPMedStudyAnnotator
from dug.utils import BioLinkPURLerizer
import dug.tranql as tql
import argparse
import logging
import json
import requests
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
    def __init__(self, host=os.environ.get('ELASTIC_API_HOST'), port=9200, indices=['concepts_index', 'variables_index', 'kg_index']):
        logger.debug (f"Connecting to elasticsearch host: {host} at port: {port}")
        self.indices = indices
        self.crawlspace = "crawl"
        self.host = os.environ.get ('ELASTIC_API_HOST', 'localhost')
        self.username = os.environ.get ('ELASTIC_USERNAME', 'elastic')
        self.password = os.environ.get ('ELASTIC_PASSWORD', 'changeme')
        self.nboost_host = os.environ.get('NBOOST_API_HOST', 'nboost')
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

    def init_indices (self):
        settings = {}
        
        # kg_index
        settings['kg_index'] = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "concept_id": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "search_targets": {"type": "text"},
                    "knowledge_graph": {
                        "type": "object",
                        "enabled": False
                    }
                }
            }
        }

        # concepts_index
        settings['concepts_index'] = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": 0
            }, 
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "name": {"type": "text"},
                    "description": {"type": "text"},
                    "type": {"type": "keyword"},
                    "search_terms": {"type": "text"},
                    "identifiers": {
                        "properties": {
                            "id": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                            "label": {"type": "text"},
                            "equivalent_identifiers": {"type": "keyword"},
                            "type": {"type": "keyword"},
                            "synonyms": {"type": "text"}
                            }
                    },
                    "optional_terms": {"type": "text"},
                    "concept_action": {"type": "text"}
                }
            }
        }

        # variables_index
        settings['variables_index'] = {
            "settings": {
                "index.mapping.coerce": "false",
                "number_of_shards": 1,
                "number_of_replicas": 0
            }, 
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "element_id": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "element_name": {"type": "text"},
                    "element_desc": {"type": "text"},
                    "element_action": {"type": "text"},
                    "search_terms": {"type": "text"},
                    "identifiers": {"type": "keyword"},
                    "collection_id": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "collection_name": {"type": "text"},
                    "collection_desc": {"type": "text"},
                    "collection_action": {"type": "text"},
                    "data_type": {"type": "text"},
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
                        body=settings[index],
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
    
    def update_doc (self, index, doc, doc_id):
        self.es.update (
            index=index,
            id=doc_id,
            body=doc
        )

    def search_concepts(self, index, query, offset=0, size=None, fuzziness=1, prefix_length=3):
        """
        Changed to query_string for and/or and exact matches with quotations.
        """
        query = {
            'query_string': {
                'query' : query,
                'fuzziness' : fuzziness,
                'fuzzy_prefix_length': prefix_length,
                'fields': ["name", "description", "search_terms", "optional_terms"],
                'quote_field_suffix': ".exact"
            },
        }
        body = json.dumps({'query': query})
        total_items = self.es.count(body=body, index=index)
        search_results = self.es.search(
            index=index,
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results

    def search_variables(self, index, concept, query, offset=0, size=None, fuzziness=1, prefix_length=3):
        """
        In variable seach, the concept MUST match one of the indentifiers in the list
        The query can match search_terms (hence, "should") for ranking.
        """
        query = {
            'bool': {
                'must': {
                        "match": {
                            "identifiers": concept
                        }
                    },
                'should': {
                    'query_string': {
                        "query": query,
                        "fuzziness": fuzziness,
                        "fuzzy_prefix_length": prefix_length,
                        "default_field": "search_terms"
                    }
                }
            }
        }
        body = json.dumps({'query': query})
        total_items = self.es.count(body=body, index=index)
        search_results = self.es.search(
            index=index,
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results

    def search_kg(self, index, unique_id, query, offset=0, size=None, fuzziness=1, prefix_length=3):
        """
        In knowledge graph search seach, the concept MUST match the unique ID
        The query MUST match search_targets.  The updated query allows for
        fuzzy matching and for the default OR behavior for the query.
        """
        query = {
            "bool": {
                "must": [
                    {"term": {
                        "concept_id.keyword": unique_id
                        }
                    },
                    {'query_string': {
                        "query": query,
                        "fuzziness": fuzziness,
                        "fuzzy_prefix_length": prefix_length,
                        "default_field": "search_targets"
                        }
                    }
                ]
            }
        }
        body = json.dumps({'query': query})
        total_items = self.es.count(body=body, index=index)
        search_results = self.es.search(
            index=index,
            body=body,
            filter_path=['hits.hits._id', 'hits.hits._type', 'hits.hits._source'],
            from_=offset,
            size=size
        )
        search_results.update({'total_items': total_items['count']})
        return search_results

    def search_nboost(self, index, query, offset=0, size=10, fuzziness=1):
        """
        Query type is now 'query_string'.
        query searches multiple fields
        if search terms are surrounded in quotes, looks for exact matches in any of the fields
        AND/OR operators are natively supported by elasticesarch queries
        """
        nboost_query = {
            'nboost': {
                'uhost': f"{self.username}:{self.password}@{self.host}",
                'uport': self.hosts[0]['port'],
                'cvalues_path': '_source.description',
                'query_path': 'body.query.query_string.query',
                'size': size,
                'from': offset,
                'default_topk': size
            },
            'query': {
                'query_string': {
                    'query': query,
                    'fuzziness': fuzziness,
                    'prefix_length': prefix_length,
                    'fields': ['name', 'description', 'instructions', 'search_targets', 'optional_targets'],
                    'quote_field_suffix': ".exact"
                }
            }
        }

        return requests.post(url=f"http://{self.nboost_host}:8000/{index}/_search", json=nboost_query).json()

    def make_crawlspace (self):
        if not os.path.exists (self.crawlspace):
            try:
                os.makedirs (self.crawlspace)
            except Exception as e:
                print (f"-----------> {e}")
                traceback.print_exc ()

    def crawl(self, concepts, concept_index, kg_index, queries, min_score=0.2,
              include_node_keys=["id", "name", "synonyms"], include_edge_keys=[],
              query_exclude_identifiers=[],
              tranql_endpoint="http://tranql.renci.org/tranql/query?dynamic_id_resolution=true&asynchronous=false"):

        '''
        This version of tagged crawl starts from identifiers within concepts.
        If an ontological term, the concept will only have one ontology identifier: itself
        If it is, for instance, a TOPMed phenotype concept, there will be multiple ontology identifiers.
        '''
        headers = {
            "accept" : "application/json",
            "Content-Type" : "text/plain"
        }

        self.make_crawlspace ()
        for concept in concepts:
            concepts[concept]['optional_terms'] = [] # Initialize answer targets
            
            ## Set tag_indexed to False; case where tag does not return KGs from TranQL
            concept_indexed = False

            ## Queries
            for identifier in concepts[concept]["identifiers"]:
                logging.debug(f"Doing id: {identifier}")
                ''' Resolve the phenotype to identifiers. '''
                
                # skip identifiers that don't normalize, or are excluded
                if not concepts[concept]["identifiers"][identifier]["label"]:
                    logging.debug(f"Skipping non-normalized identifier: {identifier}")
                    continue
                
                if identifier in query_exclude_identifiers:
                    logging.debug(f"Skipping TranQL query for exclude listed identifier: {identifier}")
                    continue

                for query_name, query_factory in queries.items():
                    
                    # Skip query if the identifier is not a valid query for the query class
                    if not query_factory.is_valid_curie(identifier):
                        logger.info(f"identifier {identifier} is not valid for query type {query_name}. Skipping!")
                        continue
                    
                    filename = f"{self.crawlspace}/{identifier}_{query_name}.json"
                    # Skip TranQL query if a file exists in the crawlspace exists already, but continue w/ answers
                    if os.path.exists(filename):
                        logger.info(f"identifier {identifier} is already crawled. Skipping TranQL query.")
                        with open (filename, 'r') as stream:
                            response = json.load(stream)

                    else:
                        query = query_factory.get_query(identifier)
                        logger.info (query)
                        response = requests.post(
                            url = tranql_endpoint,
                            headers = headers,
                            data = query).json ()

                        # Case: Skip if empty KG 
                        if not len(response['message']['knowledge_graph']['nodes']):
                            logging.debug(f"Did not find a knowledge graph for {query}")
                            continue # continue out of loop
                        
                        # Dump out to file if there's a knowledge graph
                        with open(filename, 'w') as stream:
                            json.dump(response, stream, indent=2)    
                    
                    # Get nodes in knowledge graph hashed by ids for easy lookup
                    kg = tql.QueryKG(response)

                    for answer in kg.answers:
                        # Filter out answers that fall below a minimum score
                        # TEMPORARY: Robokop stopped including scores temporarily so ignore these for time being
                        # We don't know how this filtering works;
                        # let's bring back everything for now, so we keep all synonyms
                        # If "score" in answer and answer["score"] < min_score:
                        #    continue
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

                        # Add answer synonyms to tag's list of optional targets
                        for node_id, node in answer_kg.kg.get('knowledge_graph', {}).get('nodes', {}).items() :
                            concepts[concept]['optional_terms'].append(node['name'])
                            concepts[concept]['optional_terms'] += node['synonyms'] or []
                        # Add answer to knowledge graph ES index
                        self.index_kg_answer(concepts[concept],
                                             kg_index,
                                             curie_id=identifier,
                                             knowledge_graph=answer_kg.kg,
                                             query_name=query_name,
                                             answer_node_ids=answer_node_ids)

            # Add tag with all info to tag index
            self.index_concept(concepts[concept], concept_index)

    def index_concept(self, concept, index):
        """ Index the document. """
        identifier_dict = concept['identifiers']
        concept['identifiers'] = []
        # Rearrange identifiers
        for identifier in identifier_dict:
            r_identifier = identifier_dict[identifier]
            r_identifier['id'] = identifier
            concept['identifiers'].append(r_identifier)
        
        # Make optional_terms unique
        concept['optional_terms'] = list(set(concept['optional_terms'])) 
        self.index_doc(
            index=index,
            doc=concept,
            doc_id=concept['id'])
    
    def index_variables(self, variables, index):
        for variable in variables:
            if not self.es.exists(index,variable['element_id']):
                self.index_doc(
                    index=index,
                    doc=variable,
                    doc_id=variable['element_id'])
            else:
                results = self.es.get(index, variable['element_id'])
                identifiers = results['_source']['identifiers'] + variable['identifiers'] 
                doc = {"doc" :{}}
                doc['doc']['identifiers'] = identifiers
                self.update_doc(index = index, doc = doc, doc_id = variable['element_id'])

    def index_kg_answer(self, concept, index, curie_id, knowledge_graph, query_name, answer_node_ids):
        answer_synonyms = []
        for node_id, node in knowledge_graph.get('knowledge_graph', {}).get('nodes', {}).items():
            # Don't add curie synonyms to knowledge graph
            #  We only want to return KG answer if it relates to user query
            if node["id"] == curie_id:
                continue
            answer_synonyms.append(node['name'])
            answer_synonyms += node.get('synonyms') or []

        # Create the Doc
        doc = {
            'concept_id': concept['id'],
            'search_targets': answer_synonyms,  # Make unique if duplicates
            'knowledge_graph': knowledge_graph
        }
        # Create unique ID
        logger.debug("Indexing TranQL query answer...")
        unique_doc_id = f"{doc['concept_id']}_{'_'.join(answer_node_ids)}_{query_name}"

        # DEBUG: For writing elasticsearch documents to JSON
        #with open(f'new_doc_structure/{unique_doc_id}.json', 'w') as stream:
        #    json.dump(doc, stream, indent=2)

        """ Index the document. """
        self.index_doc(
            index=index,
            doc=doc,
            doc_id=unique_doc_id)


if __name__ == '__main__':

    db_url_default = "http://" + os.environ.get('NEO4J_HOST', 'localhost') + ":" + os.environ.get('NEO4J_PORT',
                                                                                                  '7474') + "/db/data"
    
    parser = argparse.ArgumentParser(description='DUG-Search Crawler')

    # Add mutually exclusive group for whether crawl inputs are coming from file or TranQL
    parser.add_argument('--crawl-file',
                        help='Input file containing things you want to crawl/index',
                        dest="crawl_file")

    # Minimum score for Robokop answer to be included in ElasticSearch Index
    parser.add_argument('--min-tranql-score', help='Minimum score to consider an answer from TranQL',
                        dest="min_tranql_score",
                        default=0.2, type=float)

    parser.add_argument('--elastic-host', help="Elasticsearch host", action="store", dest="elasticsearch_host",
                        default=os.environ.get('ELASTIC_API_HOST', 'localhost'))
    parser.add_argument('--elastic-port', help="Elasticsearch port", action="store", dest="elasticsearch_port",
                        default=os.environ.get('ELASTIC_API_PORT', 9200))
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)

    # Initialiize Search object
    concepts_index = "concepts_index"
    variables_index = "variables_index"
    kg_index = "kg_index"
    search = Search (host=args.elasticsearch_host,
                     port=args.elasticsearch_port,
                     indices=[concepts_index, variables_index, kg_index])

    config = {
        'annotator': "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
        'normalizer': "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
        'synonym_service': "https://onto.renci.org/synonyms/",
        'ontology_metadata': "https://api.monarchinitiative.org/api/bioentity/",
        'redis_host': os.environ.get('REDIS_HOST', 'localhost'),
        'redis_port': os.environ.get('REDIS_PORT', 6379),
        'redis_password': os.environ.get('REDIS_PASSWORD', ''),
    }

    # Create annotator object
    annotator = TOPMedStudyAnnotator(config=config)

    # Use file extension to determine how to parse for now
    # Eventually we'll need something more sophisticated as we get more types
    if args.crawl_file.endswith(".csv"):
        # Read in pre-harmonized variables (tagged variables we're calling them) from csv
        variables, tags = annotator.load_tagged_variables(args.crawl_file)
        concepts = annotator.annotate(tags)
    elif args.crawl_file.endswith(".xml"):
        # Parse variables from dbgap data dictionary xml file
        variables = annotator.load_data_dictionary(args.crawl_file)
        concepts = annotator.annotate(variables)

    # Add Synonyms - this is slow: 30 secs
    concepts = annotator.add_synonyms_to_identifiers(concepts)

    # Add concept actions (i.e. external links). ATM, it makes a link to the ontology identifier PURL
    # Could be cooler stuff in the future but this'll do for now, pig.
    for concept in concepts:
        ontology_purl = BioLinkPURLerizer.get_curie_purl(concept)
        concepts[concept]["concept_action"] = ontology_purl if ontology_purl is not None else ""

    ''' New - Clean up after POC'''
    # Clean concepts and add ontology descriptors - this is slow: 60 secs
    concepts = annotator.clean_concepts(concepts)

    # TODO: Add more identifiers to variables based on Topmed tag in identifiers slot, for Proof of concept.
    # ##### Not sure if this is what we want to do.  Maybe delete this chunk after POC.
    for variable in variables:
        for identifier in variable['identifiers']:
            if identifier.startswith("TOPMED"):# if TOPMED identifier, expand
                new_vars = list(concepts[identifier]['identifiers'].keys())
                variable['identifiers'].extend(new_vars)

        # Make unique
        variable['identifiers'] = list(set(list(variable['identifiers'])))

    variable_file = open("variable_file.json", "w")
    variable_file.write(f"{json.dumps(variables, indent=2)}")
    ''' End New for POC '''

    source = "/graph/gamma/quick" #TODO: NOV 25 - Since we have synonyms, we can change this to /schema, probably.
    queries = {
        "disease": tql.QueryFactory(["disease", "phenotypic_feature"], source),
        "pheno": tql.QueryFactory(["phenotypic_feature", "disease"], source),
        "anat": tql.QueryFactory(["disease", "anatomical_entity"], source),
        "chem_to_disease": tql.QueryFactory(["chemical_substance", "disease"], source),
        "phen_to_anat": tql.QueryFactory(["phenotypic_feature", "anatomical_entity"], source),
        "anat_to_disease": tql.QueryFactory(["anatomical_entity", "disease"], source),
        "anat_to_pheno": tql.QueryFactory(["anatomical_entity", "phenotypic_feature"], source)
    }

    # List of identifiers to stay away from for now
    query_exclude_identifiers = ["CHEBI:17336"]

    # Just do the crawl
    search.crawl(concepts,
                 concepts_index,
                 kg_index,
                 queries,
                 min_score=args.min_tranql_score,
                 query_exclude_identifiers=query_exclude_identifiers)

    # TODO: Index the Variables separately (this doesn't require crawling)
    search.index_variables(variables,variables_index)
