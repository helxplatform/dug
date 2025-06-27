import logging
import os
import requests
from typing import List
from xml.etree import ElementTree as ET

from dug import utils as utils
from ._base import DugStudy, Parser, Indexable, InputFile

logger = logging.getLogger('dug')

DEFAULT_MDS_ENDPOINT = 'https://healdata.org/mds/metadata'
PUBLIC_MDS_ENDPOINT = 'https://healdata.org/portal/discovery'
MDS_DEFAULT_LIMIT = 10000
HEAL_STUDY_GUID_TYPES = [
    'discovery_metadata',                   # Fully registered studies.
    'unregistered_discovery_metadata'       # Studies added to the Platform MDS but without the investigator registering the study.
]
HDP_ID_PREFIX = 'HEALDATAPLATFORM:'

def get_study_info_from_mds(study_id:str, mds_url:str=None):
        if not mds_url:
            mds_url = DEFAULT_MDS_ENDPOINT

        result = requests.get(mds_url + '/' + study_id)
        if not result.ok:
            logger.error(f'Could not retrieve study ID {study_id}: {result}')
            return None

        study_json = result.json()

        ## Get study information from whatever sources and create a DugStudy element
        gen3_discovery = study_json.get('gen3_discovery', None)
        nih_reporter = study_json.get('nih_reporter', None)
        
        if gen3_discovery is None and nih_reporter is None:
            return None

        study_metadata = gen3_discovery.get('study_metadata', {})
        minimal_info = gen3_discovery.get('minimal_info', {})
        if not minimal_info:
                # sometimes this shows up in different places
            minimal_info = study_metadata.get('minimal_info', {})
        
        if not nih_reporter:
            print(f"No nih_reporter found in study file {study_id}, continuing.")
            nih_reporter = {}
        
        abstract = minimal_info.get('study_description', "")
        description = gen3_discovery.get("study_description_summary", "")
        abstract = "No Summary Found" if ( abstract is None or (abstract is not None and len(abstract) == 0)) else abstract
        description = "No Summary Found" if (description is None or (description is not None and len(description) == 0)) else description

        pi_list = []
        if gen3_discovery is not None and 'investigators_name' in gen3_discovery and len(gen3_discovery['investigators_name']) > 0:
                pi_list = gen3_discovery['investigators_name']
        elif study_metadata is not None and 'citation' in study_metadata and 'investigators' in study_metadata['citation']:
            pi_list = [ " ".join([k['investigator_first_name'], k["investigator_middle_initial"], k["investigator_last_name"]]) for k in study_metadata['citation']['investigators']]

        publication_list = []
        if study_metadata is not None and ('findings' in study_metadata and 'primary_publications' in study_metadata['findings']):
            publication_list = study_metadata['findings']['primary_publications']

        study_details = {
            "id": HDP_ID_PREFIX + study_id,
            "study_name" : gen3_discovery.get('project_title', ""),
            "description" : gen3_discovery.get("study_description_summary", ""),
            "action" : gen3_discovery['doi_url'] if (gen3_discovery is not None and "doi_url" in gen3_discovery and len(gen3_discovery['doi_url']) >0) else (PUBLIC_MDS_ENDPOINT + "/" + study_id), ## TODO: There's a DOI link on MDS as well. Use that when available.
            "abstract" : minimal_info.get('study_description', ""),
            "project_start_date" : nih_reporter.get('project_start_date', ""),
            "project_end_date" : nih_reporter.get('project_end_date', ""),
            "abstract": abstract,
            "description": description,
            "publication_list": publication_list,
            "pi_list": pi_list,
            'institution': gen3_discovery['institutions'] if gen3_discovery is not None and 'institutions' in gen3_discovery else '',
        }
        return study_details


class HEALStudiesParser(Parser):
    ## Class for parsing data from HEAL MDS, and creating corresponding DUG elements
    def __init__(self, study_type="HEAL Studies"):
        super()
        self.study_type = study_type
    
    def get_study_type(self):
        return self.study_type
    
    def set_study_type(self, study_type):
        self.study_type = study_type

    def __call__(self, mds_url: str=None) -> List[Indexable]:
        logger.debug(mds_url)
        
        if not mds_url:
            mds_url = DEFAULT_MDS_ENDPOINT

        metadata_ids = []
        for heal_study_guid_type in HEAL_STUDY_GUID_TYPES:
            result = requests.get(mds_url, params={
                '_guid_type': heal_study_guid_type,
                'limit': MDS_DEFAULT_LIMIT,
            })
            if not result.ok:
                logger.error(f'Could not retrieve metadata list for guid_type {heal_study_guid_type}: {result}')
                return None
            metadata_ids.extend(result.json())
        study_ids = list(metadata_ids)
        logger.info(f"Getting information for {len(study_ids)} studies from HEAL MDS")
        
        studies = []
        for count, sid in enumerate(study_ids):
                study_details = get_study_info_from_mds(study_id = sid, mds_url = mds_url)
                if study_details is None:
                    logger.debug(f"Metadata for Study {sid} is not available, Skipping!")
                    continue
                
                study = DugStudy(
                            id=study_details['id'],
                            name=study_details['study_name'],
                            description=study_details['description'],
                            program_name_list=[self.get_study_type()],
                            parents=[],
                            action = study_details['action'],
                            abstract=study_details['abstract'],
                            publications = study_details['publication_list'],
                            metadata = {
                                'Project Start Date':study_details['project_start_date'],
                                'Project End Date':study_details['project_end_date'],
                                'Institution': study_details['institution'],
                                'Investigator/s': study_details['pi_list']
                                }
                            )
                
                logger.debug(study)
                studies.append(studies)

        return studies
