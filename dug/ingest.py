import argparse
import json
import logging
import os
from dug.core import Search
from dug.annotate import TOPMedStudyAnnotator, GraphDB
from typing import Dict

logger = logging.getLogger (__name__)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

Config = Dict

def main ():
    """
    Configure an annotator.
    """
    db_url_default = "http://" + os.environ.get('NEO4J_HOST', 'localhost') + ":" + os.environ.get('NEO4J_PORT', '7474') + "/db/data"
    config = {
        'annotator'      : "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
        'normalizer'     : "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
        'synonym_service': "https://onto.renci.org/synonyms/",
        'ontology_metadata': "https://api.monarchinitiative.org/api/ontology/term/",
        'password'       : os.environ['NEO4J_PASSWORD'],
        'username'       : 'neo4j',
        'db_url'         : db_url_default,
        'redis_host'     : os.environ.get('REDIS_HOST', 'localhost'),
        'redis_port'     : os.environ.get('REDIS_PORT', 6379),
        'redis_password' : os.environ.get('REDIS_PASSWORD', ''),
    }

    parser = argparse.ArgumentParser(description='Load edges and nodes into Neo4j via kgx')
    parser.add_argument('--load', help='annotation file to load via kgx')
    parser.add_argument('--annotate', help='annotate TOPMed data dictionary file', default=None)
    parser.add_argument('--db-url', help='database url', default=db_url_default)
    parser.add_argument('--db-username', help='database username', default='neo4j')
    parser.add_argument('--db-password', help='database password', default=os.environ['NEO4J_PASSWORD'])
    parser.add_argument('--tagged', help='annotate tagged variables')
    parser.add_argument('--index', help='build search index directly. valid only with --tagged.', default=False)
    parser.add_argument('--debug', help='debug output', default=False)
    args = parser.parse_args()

    config['username'] = args.db_username
    config['password'] = args.db_password
    config['db_url']   = args.db_url
    annotator = TOPMedStudyAnnotator (config=config)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.load:
        """ Load an annotated data dictionary and write to a graph database. """
        with open(args.load, 'r') as stream:
            obj = json.load(stream)

            """ Convert. """
            knowledge_graph = annotator.convert_to_kgx_json (obj)

            """ Write output """
            annotator.write (knowledge_graph)
    elif args.annotate:

        input_file = args.annotate
        variables = annotator.load_data_dictionary (input_file) \
                    if input_file.endswith('.xml') \
                       else annotator.load_csv (input_file)

        """ Annotate an input file using the MonarchInitiative SciGraph named entity extractor and annotator. """
        response = annotator.annotate (variables)

        """ Write the annotated variables. """
        output_file = args.annotate.\
                      replace ('.xml', '_tagged.json').\
                      replace ('.csv', '_tagged.json')
        with open(output_file, 'w') as stream:
            json.dump(response, stream, indent=2)
    elif args.tagged:

        """
        The link operator for tagged variables.
        This annotates, normalizes, converts to a kgs graph, and loads via KGX into Neo4J.
        """
        variables, tags = annotator.load_tagged_variables (args.tagged)
        tags = annotator.annotate (tags)
        logger.debug (f"{json.dumps(tags, indent=2)}")
        knowledge_graph = annotator.make_tagged_kg (variables, tags)
        logger.debug (f"{json.dumps(knowledge_graph, indent=2)}")
        annotator.write (knowledge_graph)

        if (args.index):
            """ PHASE-1: Go directly to Elasticsearch, bypassing Translator. """

            """ Initialize the search engine core. """
            search = Search ()

            """ Connect to the graph database. """
            graph = GraphDB (config)

            """
            For each Biolink model category, get subgraphs initiated with the category, connected to a tag, to a variable, to a study.
            For each resulting subgraph, build a document linking data from each of these layers.
            Add the document to the search index.
            """
            for category in [ "phenotypic_feature", "anatomical_entity", "cell_type", "gene", "disease", "biological_process" ]:
                page_size= 10_000
                path_count_cypher = f"""MATCH 
                    p=(bioconcept:{category})--(tag:information_content_entity)--(variable:clinical_modifier)--(study:clinical_trial) 
                    RETURN count(p) as path_count
                """
                get_path_query = lambda skip, limit: f"MATCH" \
                    f"(bioconcept:{category})--(tag:information_content_entity)--(variable:clinical_modifier)--(study:clinical_trial)" \
                    f"RETURN * SKIP {skip} LIMIT {limit}"
                path_count = graph.query(path_count_cypher)[0][0]
                logger.debug(f"Found {path_count} paths for ({category})--(information_content_entity)"
                             "--(clinical_modifier)--(clinical_trial)")
                for offset in range(0, path_count, page_size):
                    skip = offset
                    limit = skip + page_size
                    query = get_path_query(skip, limit)
                    result = graph.query (query)
                    if result:
                        for index, row in enumerate(result.rows):
                            """
                            We're looking at a single subgraph returned from the query.
                            Build a document collecting these artifacts.
                            """

                            """ 
                            Initialize empty dict with initial values 
                            set to null so that they'll always exist 
                            """
                            doc = {'study_name': '',
                                   'description': '',
                                   'instructions': ''}

                            for node in row:
                                node_id = node['id']
                                if node_id.startswith ("TOPMED.VAR:"):
                                    doc['var'] = node_id.replace  ("TOPMED.VAR:", "")
                                elif node_id.startswith ("TOPMED.STUDY"):
                                    doc['study'] = node_id.replace ("TOPMED.STUDY:", "")
                                    doc['study_name'] = node['name']
                                elif node_id.startswith ("TOPMED.TAG"):
                                    doc['tag'] = node_id.replace ("TOPMED.TAG:", "")
                                    doc['description'] = node['description']
                                    doc['instructions'] = node['instructions']
                                else:
                                    doc['id'] = node_id
                                    doc['name'] = node['name']

                            unique_doc_id = f"{doc['id']}_{doc['study']}_{doc['var']}"
                            logger.debug (f"{json.dumps(doc, indent=2)}")

                            """ Index the document. """
                            search.index_doc (
                                index='test',
                                doc=doc,
                                doc_id=unique_doc_id)


if __name__ == '__main__':
    main ()
