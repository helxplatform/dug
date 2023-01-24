import logging
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class BACPACParser(FileParser):
    # Class for parsing BACPAC data dictionaries in dbGaP XML format into a set of Dug Elements.

    @staticmethod
    def parse_study_name_from_filename(filename: str):
        # Parse the form name from the xml filename
        return filename.split('/')[-1].replace('.xml', '')

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        logger.debug(input_file)
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']

        # Parse study name from file handle
        study_name = self.parse_study_name_from_filename(str(input_file))

        if study_name is None:
            err_msg = f"Unable to parse BACPAC Form name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        elements = []
        for variable in root.iter('variable'):
            description = variable.find('description').text or ""
            elem = DugElement(elem_id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              desc=description.lower(),
                              elem_type="BACPAC",
                              collection_id=f"{study_id}",
                              collection_name=study_name)

            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements
