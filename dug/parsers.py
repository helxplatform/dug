import csv
import json
import logging
import os
import xml.etree.ElementTree as ET
import dug.utils as utils


logger = logging.getLogger(__name__)


class DugElement:
    # Basic class for holding information for an object you want to make searchable via Dug
    # Could be a DbGaP variable, DICOM image, App, or really anything
    # Optionally can hold information pertaining to a containing collection (e.g. dbgap study or dicom image series)
    def __init__(self, elem_id, name, desc, elem_type, collection_id="", collection_name="", collection_desc=""):
        self.id = elem_id
        self.name = name
        self.description = desc
        self.type = elem_type
        self.collection_id = collection_id
        self.collection_name = collection_name
        self.collection_desc = collection_desc
        self.action = ""
        self.collection_action = ""
        self.concepts = {}
        self.ml_ready_desc = desc

    def add_concept(self, concept):
        self.concepts[concept.id] = concept

    def jsonable(self):
        return self.__dict__

    def get_searchable_dict(self):
        # Translate DugElement to ES-style dict
        es_elem = {
            'element_id': self.id,
            'element_name': self.name,
            'element_desc': self.description,
            'collection_id': self.collection_id,
            'collection_name': self.collection_name,
            'collection_desc': self.collection_desc,
            'element_action': self.action,
            'collection_action': self.collection_action,
            'data_type': self.type,
            'identifiers': list(self.concepts.keys())
        }
        return es_elem

    def __str__(self):
        return json.dumps(self.__dict__, indent=2, default=utils.complex_handler)


class DugConcept:
    # Basic class for holding information about concepts that are used to organize elements
    # All Concepts map to at least one element
    def __init__(self, concept_id, name, desc, concept_type):
        self.id = concept_id
        self.name = name
        self.description = desc
        self.type = concept_type
        self.concept_action = ""
        self.identifiers = {}
        self.kg_answers = {}
        self.search_terms = []
        self.optional_terms = []
        self.ml_ready_desc = desc

    def add_identifier(self, ident):
        if ident.id in self.identifiers:
            for search_text in ident.search_text:
                self.identifiers[ident.id].add_search_text(search_text)
        else:
            self.identifiers[ident.id] = ident

    def add_kg_answer(self, answer, query_name):
        answer_node_ids = list(answer.nodes.keys())
        answer_id = f'{"_".join(answer_node_ids)}_{query_name}'
        if answer_id not in self.kg_answers:
            self.kg_answers[answer_id] = answer

    def clean(self):
        self.search_terms = list(set(self.search_terms))
        self.optional_terms = list(set(self.optional_terms))

    def set_search_terms(self):
        # Traverse set of identifiers to determine set of search terms
        search_terms = self.search_terms
        for ident_id, ident in self.identifiers.items():
            search_terms.extend([ident.label, ident.description] + ident.search_text + ident.synonyms)
        self.search_terms = list(set(search_terms))

    def set_optional_terms(self):
        # Traverse set of knowledge graph answers to determine set of optional search terms
        optional_terms = self.optional_terms
        for kg_id, kg_answer in self.kg_answers.items():
            optional_terms += kg_answer.get_node_names()
            optional_terms += kg_answer.get_node_synonyms()
        self.optional_terms = list(set(optional_terms))

    def get_searchable_dict(self):
        # Translate DugConcept into Elastic-Compatible Concept
        es_conc = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'search_terms': self.search_terms,
            'optional_terms': self.optional_terms,
            'concept_action': self.concept_action,
            'identifiers': [ident.get_searchable_dict() for ident_id, ident in self.identifiers.items()]
        }
        return es_conc

    def jsonable(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.__dict__, indent=2, default=utils.complex_handler)


class DbGaPParser:
    # Class for parsing DBGaP Data dictionary into a set of Dug Elements

    @staticmethod
    def parse(input_file):
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']
        participant_set = root.attrib['participant_set']

        # Parse study name from filehandle
        study_name = utils.parse_study_name_from_filename(input_file)

        if study_name is None:
            err_msg = f"Unable to parse DbGaP study name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        elements = []
        for variable in root.iter('variable'):
            elem = DugElement(elem_id=f"{variable.attrib['id']}.p{participant_set}",
                              name=variable.find('name').text,
                              desc=variable.find('description').text.lower(),
                              elem_type="DbGaP",
                              collection_id=f"{study_id}.p{participant_set}",
                              collection_name=study_name)

            # Create DBGaP links as study/variable actions
            elem.collection_action = utils.get_dbgap_study_link(study_id=elem.collection_id)
            elem.action = utils.get_dbgap_var_link(study_id=elem.collection_id,
                                                   variable_id=elem.id.split(".")[0].split("phv")[1])
            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements


class TOPMedTagParser:

    @staticmethod
    def parse(input_file):
        """
        Load tagged variables.
          Presumes a harmonized variable list as a CSV file as input.
          A naming convention such that <prefix>_variables_<version>.csv will be the form of the filename.
          An adjacent file called <prefix>_tags_<version.json will exist.

          :param input_file: A list of study variables linked to tags, studies, and other relevant data.
          :returns: Returns variables, a list of parsed variable dictionaries and tags, a list of parsed
                    tag definitions linked to the variabels.
        """

        tags_input_file = input_file.replace(".csv", ".json").replace("_variables_", "_tags_")
        if not os.path.exists(tags_input_file):
            raise ValueError(f"Accompanying tags file: {tags_input_file} must exist.")

        # Read in huamn-created tags/concepts from json file before reading in elements
        with open(tags_input_file, "r") as stream:
            tags = json.load(stream)

        # Loop through tags and create concepts for each one
        concepts = {}
        for tag in tags:
            concept_id = f"TOPMED.TAG:{tag['pk']}"
            concept = DugConcept(concept_id,
                                 name=tag['fields']['title'],
                                 desc=f'{tag["fields"]["description"]}. {tag["fields"]["instructions"]}',
                                 concept_type="TOPMed Phenotype Concept")

            # Only use the description for annotation
            concept.ml_ready_desc = tag["fields"]["description"]
            concepts[str(tag['pk'])] = concept
            logger.debug(concept)

        # Now loop through associated variables and associate each with its parent concept/tag
        elements = []
        with open(input_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                row = {k.strip(): v for k, v in row.items()}
                elem = DugElement(elem_id=row['variable_full_accession'],
                                  name=row['variable_name'] if 'variable_name' in row else row['variable_full_accession'],
                                  desc=row['variable_desc'] if 'variable_name' in row else row['variable_full_accession'],
                                  elem_type="DbGaP",
                                  collection_id=row['study_full_accession'],
                                  collection_name=row['study_name'])

                # Create DBGaP links as study/variable actions
                elem.collection_action = utils.get_dbgap_study_link(study_id=elem.collection_id)
                elem.action = utils.get_dbgap_var_link(study_id=elem.collection_id,
                                                       variable_id=elem.id.split(".")[0].split("phv")[1])

                # Add concept parsed from tag file to element
                concept_group = row['tag_pk']
                if concept_group not in concepts:
                    # Raise error if the tag_id parsed from the variable file didn't exist in the tag file
                    err_msg = f"DbGaP variable '{elem.id}' maps to a tag group that doesn't exist in tag file: '{concept_group}'"
                    logger.error(err_msg)
                    raise IOError(err_msg)
                elem.add_concept(concepts[row['tag_pk']])

                # Add element to list of elements
                elements.append(elem)
                logger.debug(elem)

        return list(concepts.values()) + elements


# Register parsers with parser factory
factory = utils.ObjectFactory()
factory.register_builder("DbGaP", DbGaPParser)
factory.register_builder("TOPMedTag", TOPMedTagParser)
