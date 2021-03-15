import argparse
import logging
import json
import requests
import traceback
import os
from elasticsearch import Elasticsearch
import redis
from requests_cache import CachedSession

import dug.config as cfg
import dug.parsers as parsers
import dug.annotate as anno

logger = logging.getLogger(__name__)

logging.getLogger("elasticsearch").setLevel(logging.WARNING)


class SearchException(Exception):
    def __init__(self, message, details):
        self.message = message
        self.details = details


class ParserNotFoundException(Exception):
    pass


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

    def __init__(self, host=os.environ.get('ELASTIC_API_HOST'), port=9200,
                 indices=['concepts_index', 'variables_index', 'kg_index']):
        logger.debug(f"Connecting to elasticsearch host: {host} at port: {port}")
        self.indices = indices
        self.host = os.environ.get('ELASTIC_API_HOST', 'localhost')
        self.username = os.environ.get('ELASTIC_USERNAME', 'elastic')
        self.password = os.environ.get('ELASTIC_PASSWORD', 'changeme')
        self.nboost_host = os.environ.get('NBOOST_API_HOST', 'nboost')
        self.hosts = [
            {
                'host': self.host,
                'port': port
            }
        ]
        logger.debug(f"Authenticating as user {self.username} to host:{self.hosts}")
        self.es = Elasticsearch(hosts=self.hosts,
                                http_auth=(self.username, self.password))

        if self.es.ping():
            logger.info('connected to elasticsearch')
            self.init_indices()
        else:
            print(f"Unable to connect to elasticsearch at {host}:{port}")
            logger.error(f"Unable to connect to elasticsearch at {host}:{port}")
            raise SearchException(
                message='failed to connect to elasticsearch',
                details=f"connecting to host {host} and port {port}")

    def init_indices(self):
        settings = {}

        # kg_index
        settings['kg_index'] = {
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

        logger.info(f"creating indices: {self.indices}")
        for index in self.indices:
            try:
                if self.es.indices.exists(index=index):
                    logger.info(f"Ignoring index {index} which already exists.")
                else:
                    result = self.es.indices.create(
                        index=index,
                        body=settings[index],
                        ignore=400)
                    logger.info(f"result created index {index}: {result}")
            except Exception as e:
                logger.error(f"exception: {e}")
                raise e

    def index_doc(self, index, doc, doc_id):
        self.es.index(
            index=index,
            id=doc_id,
            body=doc)

    def update_doc(self, index, doc, doc_id):
        self.es.update(
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
                'query': query,
                'fuzziness': fuzziness,
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
                    'fields': ['name', 'description', 'instructions', 'search_targets', 'optional_targets'],
                    'quote_field_suffix': ".exact"
                }
            }
        }

        return requests.post(url=f"http://{self.nboost_host}:8000/{index}/_search", json=nboost_query).json()

    def index_concept(self, concept, index):
        """ Index the document. """
        self.index_doc(
            index=index,
            doc=concept.get_searchable_dict(),
            doc_id=concept.id)

    def index_element(self, elem, index):
        if not self.es.exists(index, elem.id):
            # If the element doesn't exist, add it directly
            self.index_doc(
                index=index,
                doc=elem.get_searchable_dict(),
                doc_id=elem.id)
        else:
            # Otherwise update to add any new identifiers that weren't there last time around
            results = self.es.get(index, elem.id)
            identifiers = results['_source']['identifiers'] + list(elem.concepts.keys())
            doc = {"doc": {}}
            doc['doc']['identifiers'] = list(set(identifiers))
            self.update_doc(index=index, doc=doc, doc_id=elem.id)

    def index_kg_answer(self, concept_id, kg_answer, index, id_suffix=None):

        # Get search targets by extracting names/synonyms from non-curie nodes in answer knoweldge graph
        search_targets = kg_answer.get_node_names(include_curie=False)
        search_targets += kg_answer.get_node_synonyms(include_curie=False)

        # Create the Doc
        doc = {
            'concept_id': concept_id,
            'search_targets': list(set(search_targets)),
            'knowledge_graph': kg_answer.get_kg()
        }

        # Create unique ID
        logger.debug("Indexing TranQL query answer...")
        id_suffix = list(kg_answer.nodes.keys()) if id_suffix is None else id_suffix
        unique_doc_id = f"{concept_id}_{id_suffix}"

        """ Index the document. """
        self.index_doc(
            index=index,
            doc=doc,
            doc_id=unique_doc_id)


class Crawler:
    def __init__(self, crawl_file, parser, annotator,
                 tranqlizer, tranql_queries,
                 http_session, exclude_identifiers=[], element_type=None):

        self.crawl_file = crawl_file
        self.parser = parser
        self.element_type = element_type
        self.annotator = annotator
        self.tranqlizer = tranqlizer
        self.tranql_queries = tranql_queries
        self.http_session = http_session
        self.exclude_identifiers = exclude_identifiers
        self.elements = []
        self.concepts = {}
        self.crawlspace = "crawl"

    def make_crawlspace(self):
        if not os.path.exists(self.crawlspace):
            try:
                os.makedirs(self.crawlspace)
            except Exception as e:
                print(f"-----------> {e}")
                traceback.print_exc()

    def crawl(self):

        # Create directory for storing temporary results
        self.make_crawlspace()

        # Read in elements from parser
        self.elements = self.parser.parse(self.crawl_file)

        # Optionally coerce all elements to be a specific type
        for element in self.elements:
            if isinstance(element, parsers.DugElement) and self.element_type is not None:
                element.type = self.element_type

        # Annotate elements
        self.annotate_elements()

        # Expand concepts
        concept_file = open(f"{self.crawlspace}/concept_file.json", "w")
        for concept_id, concept in self.concepts.items():
            # Use TranQL queries to fetch knowledge graphs containing related but not synonymous biological terms
            self.expand_concept(concept)

            # Traverse identifiers to create single list of of search targets/synonyms for concept
            concept.set_search_terms()

            # Traverse kg answers to create list of optional search targets containing related concepts
            concept.set_optional_terms()

            # Remove duplicate search terms and optional search terms
            concept.clean()

            # Write concept out to a file
            concept_file.write(f"{json.dumps(concept.get_searchable_dict(), indent=2)}")

        # Close concept file
        concept_file.close()

    def annotate_elements(self):

        # Open variable file for writing
        variable_file = open(f"{self.crawlspace}/element_file.json", "w")

        # Annotate elements/concepts and create new concepts based on the ontology identifiers returned
        for element in self.elements:
            # If element is actually a pre-loaded concept (e.g. TOPMed Tag), add that to list of concepts
            if isinstance(element, parsers.DugConcept):
                self.concepts[element.id] = element

            # Annotate element with normalized ontology identifiers
            self.annotate_element(element)
            if isinstance(element, parsers.DugElement):
                variable_file.write(f"{element}\n")

        # Now that we have our concepts and elements fully annotated, we need to
        # Make sure elements inherit the identifiers from their user-defined parent concepts
        # E.g. TOPMedTag1 was annotated with HP:123 and MONDO:12.
        # Each element assigned to TOPMedTag1 needs to be associated with those concepts as well
        for element in self.elements:
            # Skip user-defined concepts
            if isinstance(element, parsers.DugConcept):
                continue

            # Associate identifiers from user-defined concepts (see example above)
            # with child elements of those concepts
            concepts_to_add = []
            for concept_id, concept in element.concepts.items():
                for ident_id, identifier in concept.identifiers.items():
                    if ident_id not in element.concepts and ident_id in self.concepts:
                        concepts_to_add.append(self.concepts[ident_id])

            for concept_to_add in concepts_to_add:
                element.add_concept(concept_to_add)

        # Write elements out to file
        variable_file.close()

    def annotate_element(self, element):
        # Annotate with a set of normalized ontology identifiers
        identifiers = self.annotator.annotate(text=element.ml_ready_desc,
                                              http_session=self.http_session)

        # Each identifier then becomes a concept that links elements together
        for identifier in identifiers:
            if identifier.id not in self.concepts:
                # Create concept for newly seen identifier
                concept = parsers.DugConcept(concept_id=identifier.id,
                                             name=identifier.label,
                                             desc=identifier.description,
                                             concept_type=identifier.type)
                # Add to list of concepts
                self.concepts[identifier.id] = concept

            # Add identifier to list of identifiers associated with concept
            self.concepts[identifier.id].add_identifier(identifier)

            # Create association between newly created concept and element
            # (unless element is actually a user-defined concept)
            if isinstance(element, parsers.DugElement):
                element.add_concept(self.concepts[identifier.id])

            # If element is actually a user defined concept (e.g. TOPMedTag), associate ident with concept
            # Child elements of these user-defined concepts will inherit all these identifiers as well.
            elif isinstance(element, parsers.DugConcept):
                element.add_identifier(identifier)

    def expand_concept(self, concept):

        # Get knowledge graphs of terms related to each identifier
        for ident_id, identifier in concept.identifiers.items():

            # Conditionally skip some identifiers if they are listed in config
            if ident_id in self.exclude_identifiers:
                continue

            # Use pre-defined queries to search for related knowledge graphs that include the identifier
            for query_name, query_factory in self.tranql_queries.items():

                # Skip query if the identifier is not a valid query for the query class
                if not query_factory.is_valid_curie(ident_id):
                    logger.info(f"identifier {ident_id} is not valid for query type {query_name}. Skipping!")
                    continue

                # Fetch kg and answer
                kg_outfile = f"{self.crawlspace}/{ident_id}_{query_name}.json"
                answers = tranqlizer.expand_identifier(ident_id, query_factory, kg_outfile)

                # Add any answer knowledge graphs to
                for answer in answers:
                    concept.add_kg_answer(answer, query_name=query_name)


def get_parser(parser_type):
    # User parser factor to get a specific type of parser
    try:
        return parsers.factory.create(parser_type)
    except ValueError:
        # If the parser type doesn't exist throw a more helpful exception than just value error
        err_msg = f"Cannot find parser of type '{parser_type}'\n" \
            f"Supported parsers: {', '.join(parsers.factory.get_builder_types())}"
        logger.error(err_msg)
        raise ParserNotFoundException(err_msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='DUG-Search Crawler')

    # Add option for crawl file
    parser.add_argument('--crawl-file',
                        help='Input file containing things you want to crawl/index',
                        dest="crawl_file")

    # Add option for crawl file
    parser.add_argument('--parser-type',
                        help='Parser to use for parsing elements from crawl file',
                        dest="parser_type",
                        required=True)

    # Add option for crawl file
    parser.add_argument('--element-type',
                        help='[Optional] Coerce all elements to a certain data type (e.g. DbGaP Variable).\n'
                             'Determines what tab elements will appear under in Dug front-end',
                        dest="element_type",
                        default=None)

    args = parser.parse_args()

    # Read and validate dug config
    logging.basicConfig(level=logging.DEBUG)

    # Initialize Search object
    concepts_index = "concepts_index"
    variables_index = "variables_index"
    kg_index = "kg_index"

    # Build search object
    search = Search(host=cfg.elasticsearch_host,
                    port=cfg.elasticsearch_port,
                    indices=[concepts_index, variables_index, kg_index])

    # Configure redis so we can fetch things from cache when needed
    redis_connection = redis.StrictRedis(host=cfg.redis_host,
                                         port=cfg.redis_port,
                                         password=cfg.redis_password)

    http_session = CachedSession(cache_name='annotator',
                                 backend='redis',
                                 connection=redis_connection)

    if args.crawl_file:

        # Create annotation engine for fetching ontology terms based on element text
        preprocessor    = anno.Preprocessor(**cfg.preprocessor)
        annotator       = anno.Annotator(**cfg.annotator)
        normalizer      = anno.Normalizer(**cfg.normalizer)
        synonym_finder  = anno.SynonymFinder(**cfg.synonym_service)
        ontology_helper = anno.OntologyHelper(**cfg.ontology_helper)
        tranqlizer      = anno.ConceptExpander(**cfg.concept_expander)

        # Greenlist of ontology identifiers that can fail normalization and still be valid
        ontology_greenlist = cfg.ontology_greenlist if hasattr(cfg,"ontology_greenlist") else []

        # DugAnnotator combines all annotation components into single annotator
        dug_annotator = anno.DugAnnotator(preprocessor=preprocessor,
                                            annotator=annotator,
                                            normalizer=normalizer,
                                            synonym_finder=synonym_finder,
                                            ontology_helper=ontology_helper,
                                            ontology_greenlist=ontology_greenlist)

        # Get input parser based on input type
        parser = get_parser(args.parser_type)


        # Initialize crawler
        crawler = Crawler(crawl_file=args.crawl_file,
                          parser=parser,
                          annotator=dug_annotator,
                          tranqlizer=tranqlizer,
                          tranql_queries=cfg.tranql_queries,
                          http_session=http_session,
                          exclude_identifiers=cfg.tranql_exclude_identifiers,
                          element_type=args.element_type)

        # Read elements, annotate, and expand using tranql queries
        crawler.crawl()

        # Index Annotated Elements
        for element in crawler.elements:
            # Only index DugElements as concepts will be indexed differently in next step
            if not isinstance(element, parsers.DugConcept):
                search.index_element(element, index=variables_index)

        # Index Annotated/TranQLized Concepts and associated knowledge graphs
        for concept_id, concept in crawler.concepts.items():
            search.index_concept(concept, index=concepts_index)

            # Index knowledge graph answers for each concept
            for kg_answer_id, kg_answer in concept.kg_answers.items():
                search.index_kg_answer(concept_id=concept_id,
                                       kg_answer=kg_answer,
                                       index=kg_index,
                                       id_suffix=kg_answer_id)
