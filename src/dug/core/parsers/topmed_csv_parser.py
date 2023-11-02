import csv
import logging
from typing import List

from dug import utils as utils
from ._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class TOPMedCSVParser(FileParser):

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

        # Now loop through associated variables and associate each with its parent concept/tag
        elements: List[Indexable] = []
        with open(input_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                row = {k.strip(): v for k, v in row.items()}
                elem = DugElement(elem_id=row['variable_full_accession'],
                                  name=row['variable_name'],
                                  desc=row['variable_desc'],
                                  elem_type="dbGaP",
                                  collection_id=row['study_full_accession'],
                                  collection_name=row['study_name'])

                # Create DBGaP links as study/variable actions
                elem.collection_action = utils.get_dbgap_study_link(study_id=elem.collection_id)
                elem.action = utils.get_dbgap_var_link(study_id=elem.collection_id,
                                                       variable_id=elem.id.split(".")[0].split("phv")[1])

                # Add element to list of elements
                elements.append(elem)
                logger.debug(elem)

        return elements
