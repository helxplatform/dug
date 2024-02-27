import logging
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class RADxParser(FileParser):

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        tree = ET.parse(input_file, ET.XMLParser(encoding='utf-8'))
        root = tree.getroot()
        study_id = root.attrib['id']
        # Parse study name from GapExchange file, and if that fails try from file handle
        # If still None, raise an error message
        study_name = root.attrib['study_name']
        elements = []
        for variable in root.iter('variable'):
            desc = variable.find('description').text if variable.find('description') is not None else ''
            elem = DugElement(elem_id=f"{variable.attrib['id']}",
                              name=variable.find('name').text,
                              desc=desc,
                              elem_type=root.attrib['module'],
                              collection_id=f"{study_id}",
                              collection_name=study_name)

            # Create DBGaP links as study/variable actions
            elem.collection_action = utils.get_dbgap_study_link(study_id=elem.collection_id)
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements