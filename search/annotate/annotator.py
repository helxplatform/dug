import json
import Levenshtein
import logging
import requests
import sys
import traceback
import urllib
import xml.etree.ElementTree as ET

logger = logging.getLogger (__name__)

class TOPMedStudyAnnotator:
    """ Annotate TOPMed study data with semantic knowledge graph linkages. """
    
    def __init__(self,
                 config,
                 skip = []):
        self.normalizer = config['normalizer']
        self.annotator = config['annotator']
        self.skip = skip
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


def main ():
    """ 
    Given an input file, annotate each variable in it 
    based on metadata from an input set of ontologies.

    Also, skip words we don't want to consider.
    """
    config = {
        'annotator' : "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content=",
        'normalizer' : "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie="
    }
    
    input_file = sys.argv[1]

    """ Annotate an input file given a set of ontologies. """
    annotator = TOPMedStudyAnnotator (
        config=config,
        skip=[ 'ever','disease' ])
    response = annotator.annotate (input_file)

    """ Write the annotated variables. """
    output_file = input_file.replace ('.xml', '_tagged.json')
    with open(output_file, 'w') as stream:
        json.dump(response, stream, indent=2)

if __name__ == '__main__':    
    main ()


