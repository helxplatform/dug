import logging
import os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugElement, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class SciCrunchParser(FileParser):
    # Class for parsing SciCrunch Data into a set of Dug Elements

    @staticmethod
    def get_study_name(filename: str):
        
        study_name = root.attrib['study_name']
        stemname = os.path.splitext( os.path.basename(filename) )[0]
        if stemname.startswith("DOI"):
            # we want to convert file names that look like 
            # 
            # DOI:10.26275-howg-tbhj.xml to study names that look like 
            # 
            # DOI:10.26275/howg-tbhj
            #
            # perform the needed subs
            sn = stemname.replace("-", "/").replace(".xml", "")
            return sn
        return None

    @staticmethod
    def get_scicrunch_study_link(filename: str):
        # Parse the study name from the xml filename if it exists. Return None if filename isn't right format to get id from
        stemname = os.path.splitext( os.path.basename(filename) )[0]
        if stemname.startswith("DOI"):
            # we want to convert file names that look like
            #
            # DOI:10.26275-howg-tbhj.xml to URLs that look like
            #
            # https://DOI.org/10.26275/howg-tbhj.xml

            # add https:// to the start
            URL = "https://" + stemname

            # perform the rest of the subs
            sn = URL.replace("DOI:", "DOI.org/").replace("-", "/", 1).replace(".xml", "")
            return sn
        return None



    def __call__(self, input_file: InputFile) -> List[Indexable]:
        logger.debug(input_file)
        tree = ET.parse(input_file)
        root = tree.getroot()
        study_id = root.attrib['study_id']
        study_name = root.attrib['study_name']
        participant_set = root.get('participant_set','0')

        # Parse study name from file handle
        # study_name = self.parse_study_name_from_filename(str(input_file))

        if study_name is None:
            err_msg = f"Unable to retrieve SciCrunch study name from {input_file}!"
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

            # Create links as study/variable actions
            elem.collection_action = self.get_scicrunch_study_link(input_file)
            # Add to set of variables
            logger.debug(elem)
            elements.append(elem)

        # You don't actually create any concepts
        return elements
