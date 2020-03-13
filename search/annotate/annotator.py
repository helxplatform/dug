import argparse
import json
import logging
import requests
import requests_cache
import sys
import traceback
import urllib
import yaml
import xml.etree.ElementTree as ET
from kgx import NeoTransformer, JsonTransformer
from typing import List, Dict

logger = logging.getLogger (__name__)


logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

requests_cache.install_cache('http_cache')

SkipTerms = List[str]
Config = Dict

class TOPMedStudyAnnotator:
    """ Annotate TOPMed study data with semantic knowledge graph linkages. """
    
    def __init__(self, config: Config, skip : SkipTerms = []):
        self.normalizer = config['normalizer']
        self.annotator = config['annotator']
        self.db_url = config['db_url']
        self.username = config['username']
        self.password = config['password']
        self.skip = config['skip']
        
    def annotate (self, input_file : str) -> Dict:
        """
        This operates on a dbGaP data dictionary which is
          an XML formatted study with a data_table root element containing a list of variables.
        - Tag prose variable descriptions with ontology identifiers.
        - Resolve those identifiers via Translator to preferred identifiers and BioLink Model categories.
        Specifically, for each variable
          create an object to represent the variable
          perform NLP annotation of the variable based on its description
            use the Monarch NLP annotator with named entity recognition
            (add additional NLP, eg. Vanderbilt and others here...?)
          normalize the resulting identifiers using the Translator normalization API
        """
        response = []
        http_session = requests.Session()
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']
        for variable in root.iter('variable'):
            """ Get variable attributes """
            variable_id = variable.attrib['id']
            variable_name = variable.find ('name').text
            description = variable.find ('description').text.lower ()
            
            result = {
                "study_id" : study_id,
                "variable_id" : variable_id,
                "variable" : variable_name,
                "description" : description,
                "identifiers" : {}
            }
            response.append (result)
            try:
                """ Annotate ontology terms in the text. """
                encoded = urllib.parse.quote (description)
                url = f"{self.annotator}{encoded}"
                annotations = http_session.get(url).json ()
                
                """ Normalize each ontology identifier in the annotation. """
                for span in annotations.get('spans',[]):
                    for token in span.get('token',[]):
                        normalized = {}
                        curie = token.get('id', None)
                        if not curie:
                            continue
                        
                        """ Normalize the identifier with respect to the BioLink Model. """
                        url = f"{self.normalizer}{curie}"
                        try:
                            normalized = http_session.get(url).json ()

                            """ Record normalized results. """
                            normalization = normalized.get(curie, {})
                            preferred_id = normalization.get ("id", {})
                            equivalent_identifiers = normalization.get ("equivalent_identifiers", [])
                            biolink_type = normalization.get ("type", [])
                            
                            """ Build the response. """
                            if 'identifier' in preferred_id:
                                result['identifiers'][preferred_id['identifier']] = {
                                    "label" : preferred_id.get('label',''),
                                    "equivalent_identifiers" : [ v['identifier'] for v in equivalent_identifiers ],
                                    "type" : biolink_type
                                }
                            else:
                                print (f"ERROR: normaliz({curie})=>({preferred_id}). No identifier?")
                        except json.decoder.JSONDecodeError as e:
                            print (f"JSONDecoderError normalizing curie: {curie}")

            except json.decoder.JSONDecodeError as e:
                traceback.print_exc ()
            except:
                traceback.print_exc ()
                raise
        return response

    def write (self, annotations : Dict) -> None:
        """
        Convert the TOPMed metadata to KGX form.
        Import the graph to KGX
        Write the KGX graph to Neo4J
        """

        """ Convert. """
        graph = self.convert_to_kgx_json (annotations)

        """ Load. """
        json_transformer = JsonTransformer ()
        json_transformer.load (graph)

        """ Write. """
        db = NeoTransformer (json_transformer.graph,
                             self.db_url,
                             self.username,
                             self.password)
        db.save_with_unwind()        
        db.neo4j_report()
        
    def make_edge (self,
                   subj : str,
                   pred : str,
                   obj  : str,
                   edge_label : str ='association',
                   category : List[str] = []
    ):
        """ Create an edge between two nodes. """
        return {
            "subject"     : subj,
            "predicate"   : pred,
            "edge_label"  : edge_label if len(edge_label) > 0 else "n/a",
            "object"      : obj,
            "provided_by" : "renci.bdc.semanticsearch.annotator",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "OBAN:association",
            "category" : category
        }
    
    def convert_to_kgx_json (self, annotations):
        """
        Given an annotated and normalized set of study variables,
        generate a KGX compliant graph given the normalized annotations.
        Write that grpah to a graph database.
        See BioLink Model for category descriptions. https://biolink.github.io/biolink-model/notes.html
        """
        graph = {
            "nodes" : [],
            "edges" : []
        }
        edges = graph['edges']
        nodes = graph['nodes']
        
        for index, variable in enumerate(annotations):
            study_id = variable['study_id']
            if index == 0:
                """ assumes one study in this set. """
                nodes.append ({
                    "id" : study_id,
                    "category" : [ "clinical_trial" ]
                })
                
            """ connect the study and the variable. """
            edges.append (self.make_edge (
                subj=variable['variable_id'],
                edge_label='part_of',
                pred="OBO:RO_0002434",
                obj=study_id,
                category=['part_of']))
            edges.append (self.make_edge (
                subj=study_id,
                edge_label='has_part',
                pred="OBO:RO_0002434",
                obj=variable['variable_id'],
                category=['has_part']))
            
            """ a node for the variable. """
            nodes.append ({
                "id" : variable['variable_id'],
                "name" : variable['variable'],
                "description" : variable['description'],
                "category" : [ "clinical_modifier" ]
            })
            for identifier, metadata in variable['identifiers'].items ():
                edges.append (self.make_edge (
                    subj=variable['variable_id'],
                    pred="OBO:RO_0002434",
                    obj=identifier,
                    edge_label='association',
                    category=[ "case_to_phenotypic_feature_association" ]))
                edges.append (self.make_edge (
                    subj=identifier,
                    pred="OBO:RO_0002434",
                    obj=variable['variable_id'],
                    edge_label='association',
                    category=[ "case_to_phenotypic_feature_association" ]))
                nodes.append ({
                    "id" : identifier,
                    "name" : metadata['label'],
                    "category" : metadata['type']
                })
        return graph

def main ():
    """ 
    Configure an annotator. 
    """
    config = {
        'annotator'  : "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
        'normalizer' : "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
        'password'   : 'topmed',
        'username'   : 'neo4j',
        'db_url'     : "http://localhost:7474/db/data",
        'skip'       : [ 'ever', 'disease' ]
    }
    
    parser = argparse.ArgumentParser(description='Load edges and nodes into Neo4j via kgx')
    parser.add_argument('--load', help='annotation file to load via kgx')
    parser.add_argument('--annotate', help='annotate TOPMed data dictionary file', default=None)
    parser.add_argument('--db-url', help='database url', default='http://localhost:7474/db/data')
    parser.add_argument('--db-username', help='database username', default='neo4j')
    parser.add_argument('--db-password', help='database username', default='topmed')
    args = parser.parse_args()

    config['username'] = args.db_username
    config['password'] = args.db_password
    config['db_url']   = args.db_url
    annotator = TOPMedStudyAnnotator (config=config)
    
    if args.load:
        """ Load an annotated data dictionary and write to a graph database. """
        with open(args.load, 'r') as stream:
            obj = json.load(stream)
            annotator.write (obj)
    elif args.annotate:
        
        """ Annotate an input file using the MonarchInitiative SciGraph named entity extractor and annotator. """
        response = annotator.annotate (args.annotate)
        
        """ Write the annotated variables. """
        output_file = args.annotate.replace ('.xml', '_tagged.json')
        with open(output_file, 'w') as stream:
            json.dump(response, stream, indent=2)
        
if __name__ == '__main__':    
    main ()


