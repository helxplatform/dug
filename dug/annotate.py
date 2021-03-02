import csv
import json
import logging
import os
import redis
import traceback
import re
import urllib
import xml.etree.ElementTree as ET
from requests_cache import CachedSession
from typing import Dict

logger = logging.getLogger (__name__)

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

Config = Dict


def get_dbgap_var_link(study_id, variable_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/variable.cgi"
    return f'{base_url}?study_id={study_id}&phv={variable_id}'


def get_dbgap_study_link(study_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi"
    return f'{base_url}?study_id={study_id}'


def parse_study_name_from_filename(filename):
    # Parse the study name from the xml filename if it exists. Return None if filename isn't right format to get id from
    dbgap_file_pattern = re.compile(r'.*/*phs[0-9]+\.v[0-9]\.pht[0-9]+\.v[0-9]\.(.+)\.data_dict.*')
    match = re.match(dbgap_file_pattern, filename)
    if match is not None:
        return match.group(1)
    return None


class Debreviator:
    """ Expand certain abbreviations to increase our hit rate."""
    def __init__(self):
        self.decoder = {
            "bmi" : "body mass index"
        }

    def decode(self, text):
        for key, value in self.decoder.items():
            text = text.replace(key, value)
        return text


class TOPMedStudyAnnotator:
    """
    Annotate TOPMed study data with semantic knowledge graph linkages.

    """
    def __init__(self, config: Config):
        self.normalizer = config['normalizer']
        self.annotator = config['annotator']
        self.synonym_service = config['synonym_service']
        self.ontology_metadata = config['ontology_metadata']
        self.redis_host = config['redis_host']
        self.redis_port = config['redis_port']
        self.redis_password = config['redis_password']
        self.debreviator = Debreviator ()

    def load_data_dictionary (self, input_file : str) -> Dict:
        """
        This loads a data dictionary. It's unclear if this will be useful going forwar. But for now,
        it demonstrates how much of the rest of the  pipeline might be applied to data dictionaries.
        """
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']
        participant_set = root.attrib['participant_set']

        # Parse study name from filehandle
        study_name = parse_study_name_from_filename(input_file)
        if study_name is None:
            err_msg = f"Unable to parse DbGaP study name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        variables = [{
            "element_id"        : f"{variable.attrib['id']}.p{participant_set}",
            "element_name"      : variable.find ('name').text,
            "element_desc"      : variable.find ('description').text.lower(),
            "collection_id"     : f"{study_id}.p{participant_set}",
            "collection_name"   : study_name,
            "collection_desc"   : "",
            "data_type": "dbGap_variable",
            "identifiers": {}
        } for variable in root.iter('variable')]

        # Create DBGaP links as study/variable actions
        for variable in variables:
            variable["collection_action"] = get_dbgap_study_link(study_id = variable["collection_id"])
            variable["element_action"] = get_dbgap_var_link(study_id = variable["collection_id"],
                                                               variable_id=variable["element_id"].split(".")[0].split("phv")[1])
        return variables

    def load_tagged_variables (self, input_file : str) -> Dict:
        """
        Load tagged variables.
          Presumes a harmonized variable list as a CSV file as input.
          A naming convention such that <prefix>_variables_<version>.csv will be the form of the filename.
          An adjacent file called <prefix>_tags_<version.json will exist.

          :param input_file: A list of study variables linked to tags, studies, and other relevant data.
          :returns: Returns variables, a list of parsed variable dictionaries and tags, a list of parsed
                    tag definitions linked to the variabels.
        """
        tags_input_file = input_file.replace (".csv", ".json").replace ("_variables_", "_tags_")
        if not os.path.exists (tags_input_file):
            raise ValueError (f"Accompanying tags file: {tags_input_file} must exist.")
        variables = []
        headers = "tag_pk 	tag_title 	variable_phv 	variable_full_accession 	dataset_full_accession 	study_full_accession 	study_name 	study_phs 	study_version 	created 	modified"
        with open(input_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t',)
            for row in reader:
                better_row = { k.strip () : v for  k, v in row.items () }
                row = better_row
                logger.debug(f"{json.dumps(row, indent=2)}")
                variables.append ({
                    "element_id"                     : f"{row['variable_full_accession']}",
                    "element_name"                   : row['variable_name'] if 'variable_name' in row else row['variable_full_accession'],
                    "element_desc"            : row['variable_desc'] if 'variable_name' in row else row['variable_full_accession'],
                    "collection_id"               : f"{row['study_full_accession']}",
                    "collection_name"             : row['study_name'],
                    "collection_desc"      : "",
                    "data_type": "dbGap_variable",
                    "identifiers": [f"TOPMED.TAG:{row['tag_pk']}"]
                })
                logger.debug(f"{json.dumps(variables[-1], indent=2)}")

        # Create DBGaP links as study/variable actions
        for variable in variables:
            variable["element_action"] = get_dbgap_study_link(study_id=variable["collection_id"])
            variable["collection_action"] = get_dbgap_var_link(study_id=variable["collection_id"],
                                                               variable_id=variable["element_id"])
        # Create concepts for each tag
        with open(tags_input_file, "r") as stream:
            tags = json.load (stream)
        for tag in tags:
            for f, v in tag['fields'].items ():
                tag[f] = v
            del tag[f]
            tag['id'] = f"TOPMED.TAG:{tag['pk']}"
            tag['identifiers'] = {}
            tag['is_variable_tag'] = True
            tag['type'] = 'TOPMed Phenotype Concept'

        return variables, tags

    def normalize(self, http_session, curie, url, variable) -> None:
        """ Given an identifier (curie), use the Translator SRI node normalization service to
            find a preferred identifier, equivalent identifiers, and biolink model types for the node.

            :param http_session: A requests session to use for HTTP requests.
            :param curie: The identifier to normalize.
            :param url: The URL to use.
            :param variable: The variable in which to record the normalized identifier.
        """
        """
        Added blank_preferred_id to keep terms in the KG that fail to normalize.
        """
        blank_preferred_id = {
            "label": "",
            "equivalent_identifiers": [],
            "type": ['biolink:NamedThing'] # Default NeoTransformer category
        }
        """ Normalize the identifier with respect to the BioLink Model. """

        logger.debug(f"Normalizing: {curie}")
        normalized = http_session.get(url).json ()

        """ Record normalized results. """
        normalization = normalized.get(curie, {})
        if normalization is None:
            variable['identifiers'][curie] = blank_preferred_id
            logger.error (f"Normalization service did not return normalization for: {curie}")
            return

        preferred_id = normalization.get ("id", {})
        equivalent_identifiers = normalization.get ("equivalent_identifiers", [])
        biolink_type = normalization.get ("type", [])

        """ Build the response. """
        if 'identifier' in preferred_id:
            logger.debug(f"Preferred id: {preferred_id}")
            variable['identifiers'][preferred_id['identifier']] = {
                "label" : preferred_id.get('label',''),
                "equivalent_identifiers" : [ v['identifier'] for v in equivalent_identifiers ],
                "type" : biolink_type
            }
        else:
            variable['identifiers'][curie] = blank_preferred_id
            logger.debug (f"ERROR: normaliz({curie})=>({preferred_id}). No identifier?")

    def annotate (self, variables : Dict) -> Dict:
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

          :param variables: A dictionary of variables.
          :returns: A dictionary of annotated variables.
        """

        """
        Initialize and reuse a cached HTTP session for more efficient connection management.
        Use the Redis backend for requests-cache to store results accross executions
        """
        redis_connection = redis.StrictRedis (host=self.redis_host,
                                              port=self.redis_port,
                                              password=self.redis_password)
        http_session = CachedSession (
            cache_name='annotator',
            backend="redis",
            connection=redis_connection)

        variable_file = open("normalized_inputs.txt", "w")

        # Initialize return dict
        concepts = {}
        norm_fails = open("norm_fails.txt", "w")

        """ Annotate and normalize each tag. """
        for variable in variables:
            logger.debug(variable)
            try:
                """
                If the variable has an Xref identifier, normalize it.
                This data is only in the CSV formatted harmonized variable data.
                If that format goes away, delete this.
                """
                if 'xref' in variable:
                    self.normalize (http_session,
                                    variable['xref'],
                                    f"{self.normalizer}{variable['xref']}",
                                    variable)

                """ Annotate ontology terms in the text. """
                if 'element_desc' not in variable and 'description' not in variable:
                    logger.warn (f"this variable has no description: {json.dumps(variable, indent=2)}")
                    continue

                # Use different desc field based on whether we're dealing with a variable tag vs. just a normal variable
                description_field = "description" if "is_variable_tag" in variable else "element_desc"
                description = variable[description_field].replace ("_", " ")
                description = self.debreviator.decode (description)

                # Annotation
                encoded = urllib.parse.quote (description)
                url = f"{self.annotator}{encoded}"
                annotations = http_session.get(url).json ()

                """ Normalize each ontology identifier from the annotation. """
                for span in annotations.get('spans',[]):
                    search_text = span.get('text',None) # Always a string
                    for token in span.get('token',[]):
                        curie = token.get('id', None)
                        if not curie:
                            continue
                        self.normalize (http_session,
                                        curie,
                                        f"{self.normalizer}{curie}",
                                        variable)

                        # Skip if failing normalization
                        #TODO Address this failing normalization.
                        if curie not in variable['identifiers']:
                            norm_fails.write(f"{curie}\n")
                            continue

                        # Add concepts
                        term = token.get('terms', None) # Always a list
                        if curie not in concepts:
                            concepts[curie] = {
                                "id": curie,
                                "name": term[0],
                                "description": "",
                                "type": "",
                                "search_terms": [search_text] + term,
                                "identifiers": {
                                    curie: variable['identifiers'][curie]
                                }
                            }
                        else:
                            concepts[curie]["search_terms"].extend([search_text] + term)

            except json.decoder.JSONDecodeError as e:
                traceback.print_exc ()
            except:
                traceback.print_exc ()
                raise
            variable_file.write(f"{json.dumps(variable, indent=2)}\n")

            # Optionally create a concept when variable is actually a pre-harmonized variable tag (e.g. TOPMed tags)
            if "is_variable_tag" in variable:
                concepts[variable['id']] = {
                    "id": variable['id'],
                    "name": variable['title'],
                    "description": f"{description}. {variable['instructions']}",
                    "type": variable["type"],
                    "search_terms": [],
                    "identifiers" : variable['identifiers']
                }

        return concepts

    def add_synonyms_to_identifiers(self, concepts):
        '''
        This function does the following:
        - Initialize http_session for NCATS synonym service
        - list comprehension of all identifiers attached to tags
        - Add synonyms to all tags
        '''
        # Create an http_session like in annotate()
        redis_connection = redis.StrictRedis (host=self.redis_host,
                                              port=self.redis_port,
                                              password=self.redis_password)
        http_session = CachedSession (
            cache_name='annotator',
            backend="redis",
            connection=redis_connection)

        # Go through identifiers in tags
        for concept in concepts:
            for identifier in list(concepts[concept]['identifiers'].keys()):
                try:
                    # Get response from synonym service
                    encoded = urllib.parse.quote (identifier)
                    url = f"{self.synonym_service}{encoded}"
                    raw_synonyms = http_session.get(url).json ()

                    # List comprehension for synonyms
                    synonyms = [synonym['desc'] for synonym in raw_synonyms]
                    
                    # Add to identifier
                    concepts[concept]['identifiers'][identifier]['synonyms'] = synonyms
                    
                    # Add to search terms
                    concepts[concept]['search_terms'] += synonyms
                
                except json.decoder.JSONDecodeError as e:
                    concepts[concept]['identifiers'][identifier]['synonyms'] = []
                    logger.error (f"No synonyms returned for: {identifier}")
        return concepts
    
    def clean_concepts(self, concepts):
        '''
        This function does the following:
        - Make search terms within concepts unique
        - Write concepts to a debug file
        - Add more identifiers to variables for Proof of Concept
        - Add name/description to ontology IDs
        '''
        # Create an http_session like in annotate()
        redis_connection = redis.StrictRedis (host=self.redis_host,
                                              port=self.redis_port,
                                              password=self.redis_password)
        http_session = CachedSession (
            cache_name='annotator',
            backend="redis",
            connection=redis_connection)
        
        # Clean Concepts
        for concept in concepts:
            concepts[concept]['search_terms'] = list(set(list(concepts[concept]['search_terms'])))
        
        # Add Name and description
        for concept in concepts:
            try:
                # Get response from synonym service
                encoded = urllib.parse.quote (concept)
                url = f"{self.ontology_metadata}{encoded}"
                response = http_session.get(url).json ()

                # List comprehension for synonyms
                name = response.get('label','')
                description = '' if not response.get('description',None) else response.get('description','')
                ontology_type = '' if not response.get('category', None) else response.get('category','')[0]
                
                # Add to concept
                if len(name):
                    concepts[concept]['name'] = name
                if len(description):
                    concepts[concept]['description'] = description
                if len(ontology_type):
                    concepts[concept]['type'] = ontology_type
            
            except json.decoder.JSONDecodeError as e:
                logger.error (f"No labels returned for: {concept}")
        
        # Write to file
        concept_file = open("concept_file.json", "w")
        concept_file.write(f"{json.dumps(concepts, indent=2)}")
        
        return concepts
