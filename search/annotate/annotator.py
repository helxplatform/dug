import argparse
import json
import logging
import requests
import sys
import traceback
import urllib
import xml.etree.ElementTree as ET

from kgx import NeoTransformer, JsonTransformer
from typing import List, Dict

logger = logging.getLogger (__name__)

class TOPMedStudyAnnotator:
    """ Annotate TOPMed study data with semantic knowledge graph linkages. """
    
    def __init__(self, config: Dict[str, str], skip = []):
        self.normalizer = config['normalizer']
        self.annotator = config['annotator']
        self.db_url = config['db_url']
        self.username = config['username']
        self.password = config['password']
        self.skip = config['skip']
        self.cache = {}
        
    def annotate (self, input_file):
        """
        Tag prose descriptions with ontology identifiers. 
        This operates on a dbGaP XML formatted study with a data_table root element.
        For each variable
          for each configured ontology
            for each entity in the ontology
              for each synonym and label of the entity
                do a series of tests to determine if the entity is related to the study variable
                  (presumably use vanderbilt's nlp or scigraph or all of the above plus more)
                if the identifier is a match for this variable
                  normalize the identifier with respect to the BioLink Model
                  add the normalized entity to the list of associated identifiers for this variable
        """
        response = []
        similarity_threshold = 2
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
                annotations = self.cache[url] if url in self.cache else requests.get(url).json ()
                self.cache[url] = annotations
                
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
                            normalized = self.cache[url] if url in self.cache else requests.get(url).json ()
                            self.cache[url] = normalized
                        except json.decoder.JSONDecodeError as e:
                            print (f"error normalizing curie: {curie}")

                        """ Register results. """
                        preferred_id = normalized.get(curie, {}).get ("id", {})
                        equivalent_identifiers = normalized.get(curie, {}).get ("equivalent_identifiers", [])
                        equivalent_identifiers = [ v['identifier'] for v in equivalent_identifiers ]
                        biolink_type = normalized.get(curie, {}).get ("type", [])

                        """ Build the response. """
                        if 'identifier' in preferred_id:
                            result['identifiers'][preferred_id['identifier']] = {
                                "label" : preferred_id.get('label',''),
                                "equivalent_identifiers" : equivalent_identifiers,
                                "type" : biolink_type
                            }
                        else:
                            print (f"ERROR: curie:{curie} returned preferred id: {preferred_id}")
            except json.decoder.JSONDecodeError as e:
                traceback.print_exc ()
            except:
                traceback.print_exc ()
                raise
        return response

    def write (self, annotations) -> None:
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
        
    def make_edge (self, subj, pred, obj, edge_label='association', category=[]):
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
        print (f"{json.dumps(graph,indent=2)}")
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
    annotator = TOPMedStudyAnnotator (config=config)
    
    parser = argparse.ArgumentParser(description='Load edges and nodes into Neo4j via kgx')
    parser.add_argument('--load', help='annotation file to load via kgx')
    parser.add_argument('--annotate', help='annotate TOPMed data dictionary file', default=None)
    args = parser.parse_args()

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


