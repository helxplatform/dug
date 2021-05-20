import csv
import json
import logging
import os
from typing import List

from dug import utils as utils
from ._base import DugConcept, DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class TOPMedTagParser(FileParser):

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        """
        Load tagged variables.
        Presumes a harmonized variable list as a CSV file as input.
        A naming convention such that <prefix>_variables_<version>.csv will be the form of the filename.
        An adjacent file called <prefix>_tags_<version.json will exist.

        :param input_file: A list of study variables linked to tags, studies, and other relevant data.
        :returns: Returns variables, a list of parsed variable dictionaries and tags, a list of parsed
                  tag definitions linked to the variabels.
        """

        logger.debug(input_file)
        if not input_file.endswith(".csv"):
            return []
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
        elements: List[Indexable] = []
        with open(input_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                row = {k.strip(): v for k, v in row.items()}
                elem = DugElement(elem_id=row['variable_full_accession'],
                                  name=row['variable_name'] if 'variable_name' in row else row['variable_full_accession'],
                                  desc=row['variable_desc'] if 'variable_desc' in row else row['variable_full_accession'],
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
