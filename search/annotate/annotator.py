import requests
import json
import Levenshtein
import sys
import traceback
import xml.etree.ElementTree as ET

class TOPMedStudyAnnotator:
    """ Annotate TOPMed study data with semantic knowledge graph linkages. """
    
    def __init__(self,
                 node_normalization="https://nodenormalization-sri.renci.org/get_normalized_nodes?curie=",
                 skip = [],
                 ontologies = []):
        self.node_normalization = node_normalization 
        self.skip = skip
        self.ontologies = []
        for ontology_source in ontologies:
            with open (ontology_source, "r") as stream:
                self.ontologies.append (json.load(stream))
        
    def annotate (self, input_file):
        """
        Tag english prose descriptions with ontology identifiers. 
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

            similar_enough = int(len(description) * 0.3)
            for ontology in self.ontologies:
                for graph in ontology['graphs']:
                    for node in graph['nodes']:
                        id = node['id']
                        """ Get synonyms and label """
                        syns = map(lambda v : v['val'], node.get('meta',{}).get('synonyms',[]))
                        label = node.get('label', None)
                        if label:
                            syns.append (label) 
                        if isinstance (syns, str):
                            syns = [ syns ]
                        """ Iterate over all names for this thing. """
                        for syn in syns:
                            match = False
                            """ There seem to be some spurious synonyms ... TODO """
                            if syn in self.skip or len(syn) <= 3:
                                continue
                            if syn.isupper ():
                                """ Consider direct matches for acronyms """
                                match = syn == description
                            else:
                                """ This is useless - replace with great NLP """
                                match = Levenshtein.distance (syn, description) < similar_enough
                            if not match:
                                """ Look for the presence of the synonym in the text """
                                match = f" {syn} " in description
                            if match:
                                """ Ok, this variable seems to be related to this ontology entity. """
                                normalized = {}
                                curie = id
                                try:
                                    """ Normalize the identifier with respect to the BioLink Model. """
                                    curie = id.split('/')[-1].replace('_',':')
                                    url = f"{self.node_normalization}{curie}"
                                    normalized = requests.get (url).json ()
                                except:
                                    traceback.print_exc ()
                                preferred_id = normalized.get(curie, {}).get ("id", {})
                                equivalent_identifiers = normalized.get(curie, {}).get ("equivalent_identifiers", [])
                                equivalent_identifiers = [ v['identifier'] for v in equivalent_identifiers ]
                                biolink_type = normalized.get(curie, {}).get ("type", [])
                                if 'identifier' in preferred_id:
                                    result['identifiers'][preferred_id['identifier']] = {
                                        "label" : preferred_id.get('label',''),
                                        "synonym" : syn,
                                        "equivalent_identifiers" : equivalent_identifiers,
                                        "type" : biolink_type
                                    }
                                else:
                                    print (f"ERROR: curie:{curie} returned preferred id: {preferred_id}")
        return response

def main ():
    """ 
    Given an input file, annotate each variable in it 
    based on metadata from an input set of ontologies.

    Also, skip words we don't want to consider.
    """
    input_file = sys.argv[1]

    """ Annotate an input file given a set of ontologies. """
    annotator = TOPMedStudyAnnotator (
        skip=[ 'ever','disease' ],
        ontologies=[ 'mondo.json' ])
    response = annotator.annotate (input_file)

    """ Write the annotated variables. """
    output_file = input_file.replace ('.xml', '_tagged.json')
    with open(output_file, 'w') as stream:
        json.dump(response, stream, indent=2)

if __name__ == '__main__':    
    main ()


