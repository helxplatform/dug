import logging
import re, os
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from pathlib import Path
from dug_data_model.v2 import DugVariable, DugStudy, FileParser, Indexable, InputFile

logger = logging.getLogger('dug')


class BDCParser(FileParser):
    # Class for parsers DBGaP Data dictionary into a set of Dug Elements

    @staticmethod
    def parse_study_name_from_filename(filename: str) -> str:
        # Parse the study name from the xml filename if it exists. Return None if filename isn't right format to get id from
        dbgap_file_pattern = re.compile(r'.*/*phs[0-9]+\.v[0-9]+\.pht[0-9]+\.v[0-9]+\.(.+)\.data_dict.*')
        match = re.match(dbgap_file_pattern, filename)
        if match is not None:
            return match.group(1)
        return None
    
    @staticmethod
    def _find_gap_exchange_file(filepath: Path):
        # Find the GapExchange file adjacent to the file passed in
        parent_dir = filepath.parent.absolute()
        gap_exchange_filename_str = "GapExchange_" + parent_dir.name
        for item in os.scandir(parent_dir):
            if item.is_file and gap_exchange_filename_str in item.name:
                return item.path
        return None

    @staticmethod
    def parse_study_name_from_gap_exchange_file(filepath: Path) -> str:
        # Parse the study name from the GapExchange file adjacent to the file passed in
        gap_exchange_filepath = BDCParser._find_gap_exchange_file(filepath)
        if gap_exchange_filepath is None:
            return None
        tree = ET.parse(gap_exchange_filepath, ET.XMLParser(encoding='iso-8859-5'))
        tree_root = tree.getroot()
        return tree_root.find("./Studies/Study/Configuration/StudyNameEntrez").text

    @staticmethod
    def parse_study_description_from_gap_exchange_file(filepath: Path) -> str:
        # Parse the study description from the GapExchange file adjacent to the file passed in
        gap_exchange_filepath = BDCParser._find_gap_exchange_file(filepath)
        if gap_exchange_filepath is None:
            return ""
        tree = ET.parse(gap_exchange_filepath, ET.XMLParser(encoding='iso-8859-5'))
        tree_root = tree.getroot()
        desc_elem = tree_root.find("./Studies/Study/Configuration/Description")
        if desc_elem is not None and desc_elem.text:
            return desc_elem.text.strip()
        return ""


    def _get_program_name(self):
        return "dbGaP"

    def __call__(self, input_file: InputFile) -> List[Indexable]:
        logger.debug(input_file)
        if "GapExchange" in str(input_file).split("/")[-1]:
            msg = f"Skipping parsing for GapExchange file: {input_file}!"
            logger.info(msg)
            return []
        tree = ET.parse(input_file, ET.XMLParser(encoding='iso-8859-5'))
        root = tree.getroot()
        raw_study_id = root.attrib['study_id']
        participant_set = root.get('participant_set', '0')
        study_id = f"{raw_study_id}.p{participant_set}"

        # Parse study name from GapExchange file, and if that fails try from file handle
        # If still None, raise an error message
        study_name = self.parse_study_name_from_gap_exchange_file(Path(input_file))
        if study_name is None:
            study_name = self.parse_study_name_from_filename(str(input_file))
        if study_name is None:
            err_msg = f"Unable to parse DbGaP study name from data dictionary: {input_file}!"
            logger.error(err_msg)
            raise IOError(err_msg)

        # Parse study description from GapExchange file if available
        study_description = self.parse_study_description_from_gap_exchange_file(Path(input_file))

        variables = []
        variable_ids = []
        for variable in root.iter('variable'):
            var_id = f"{variable.attrib['id']}.p{participant_set}"
            desc_elem = variable.find('description')
            desc_text = desc_elem.text.lower() if desc_elem is not None and desc_elem.text else ""
            type_elem = variable.find('type')
            data_type = type_elem.text if type_elem is not None and type_elem.text else "text"

            var = DugVariable(
                id=var_id,
                name=variable.find('name').text,
                description=desc_text,
                action=utils.get_dbgap_var_link(study_id=study_id,
                                                variable_id=var_id.split(".")[0].split("phv")[1]),
                parents=[study_id],
                parent_type="study",
                programs=[self._get_program_name()],
                data_type=data_type
            )

            logger.debug(var)
            variables.append(var)
            variable_ids.append(var_id)

        # Create study object
        study = DugStudy(
            id=study_id,
            name=study_name,
            description=study_description,
            action=utils.get_dbgap_study_link(study_id=study_id),
            programs=[self._get_program_name()],
            variable_list=variable_ids
        )

        return [study] + variables


class AnvilBDCParser(BDCParser):
    def _get_program_name(self):
        return "AnVIL"


class CRDCBDCParser(BDCParser):
    def _get_program_name(self):
        return "Cancer Data Commons"


class KFDRCBDCParser(BDCParser):
    def _get_program_name(self):
        return "Kids First"


class BioLINCCBDCParser(BDCParser):
    def _get_program_name(self):
        return "BioLINCC"


class Covid19BDCParser(BDCParser):
    def _get_program_name(self):
        return "COVID19"


class DIRBDCParser(BDCParser):
    def _get_program_name(self):
        return "DIR"


class LungMAPBDCParser(BDCParser):
    def _get_program_name(self):
        return "LungMAP"


class NSRRBDCParser(BDCParser):
    def _get_program_name(self):
        return "NSRR"


class ParentDBGaPParser(BDCParser):
    def _get_program_name(self):
        return "Parent"


class PCGCBDCParser(BDCParser):
    def _get_program_name(self):
        return "PCGC"


class RECOVERDBGaPParser(BDCParser):
    def _get_program_name(self):
        return "RECOVER"


class TopmedDBGaPParser(BDCParser):
    def _get_program_name(self):
        return "TOPMed"


class CureSC(BDCParser):
    def _get_program_name(self):
        return "CureSC"

class HeartFailure(BDCParser):
    def _get_program_name(self):
        return "HeartFailure"
    
class Imaging(BDCParser):
    def _get_program_name(self):
        return "Imaging"
    
class Reds(BDCParser):
    def _get_program_name(self):
        return "Reds"