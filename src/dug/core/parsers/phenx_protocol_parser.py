import csv
import logging

from typing import List
import pandas as pd
# from dug.core.parsers._base import FileParser, InputFile, DugElement, DugConcept, Indexable
from ._base import FileParser, InputFile, DugElement, DugConcept, Indexable
from dug.core.annotate import Normalizer
logger = logging.getLogger('dug')



class PhenXParser(FileParser):
    PHENX_COL_NAME_NAME = 'PhenX Protocol'
    PHENX_COL_NAME_ID = 'PhenX ID'
    LOINC_COL_NAME_NAME = 'LOINC Name'
    LOINC_COL_NAME_ID = 'LOINC Code'
    CDE_COL_NAME_NAME = 'CDE Name'
    CDE_COL_NAME_ID = 'CDE Code'

    PHENX_CURIE_PREFIX = 'PhenX:'
    LOINC_CURIE_PREFIX = 'LOINC:'
    CDE_CURIE_PREFIX = 'CDE:'

    @staticmethod
    def get_parsed_row(file_name):
        read_file = pd.read_excel(file_name)
        df = pd.DataFrame(read_file)
        cols = df.columns
        # col_pairs = [(cols[i], cols[i + 1]) for i in range(0, len(cols) - 4, 2) if i < len(cols)]
        rows_all = []
        for row in df.iterrows():
            row_dict = {}
            for col_name in cols:  # , col_id in col_pairs:
                # col_to_curie_prefix_map = {'PhenX': 'PhenX', 'LOINC': 'LOINC', 'CDE': 'CDE'}
                if pd.notna(row[1][col_name]):
                    row_dict[col_name] = str(row[1][col_name]).strip()
            yield row_dict

    def __call__(self, input_file: InputFile)-> List[Indexable]:
        logger.info(input_file)
        cde_elements = []
        loinc_elements = []
        phenx_elements = []
        other_concepts = []
        for row in PhenXParser.get_parsed_row(input_file):
            phenx_element = None
            loinc_element = None
            if PhenXParser.PHENX_COL_NAME_NAME in row and PhenXParser.PHENX_COL_NAME_ID in row:
                phenx_element = DugElement(
                    elem_id=row[PhenXParser.PHENX_COL_NAME_ID],
                    name=row[PhenXParser.PHENX_COL_NAME_NAME],
                    desc = row[PhenXParser.PHENX_COL_NAME_NAME],
                    elem_type='PhenX',
                    collection_id='',
                    collection_name=''
                )
            if PhenXParser.LOINC_COL_NAME_NAME in row and PhenXParser.LOINC_COL_NAME_ID in row:
                loinc_element = DugElement(
                    elem_id=row[PhenXParser.LOINC_COL_NAME_ID],
                    name=row[PhenXParser.LOINC_COL_NAME_NAME],
                    desc = row[PhenXParser.LOINC_COL_NAME_NAME],
                    elem_type='LOINC',
                    collection_id='',
                    collection_name=''
                )
            cde_col_keys = [x for x in row.keys() if x.startswith('CDE')]
            name_cols = []
            id_cols = []
            for col in cde_col_keys:
                if PhenXParser.CDE_COL_NAME_NAME in col:
                    name_cols.append(col)
                if PhenXParser.CDE_COL_NAME_ID in col:
                    id_cols.append(col)
            current_cdes = []
            current_concepts = []
            for name, iD in zip(sorted(name_cols), sorted(id_cols)):
                if 'HP_' in row[iD]:
                    iD = iD.replace('HP_', 'HP:')
                is_concept = False
                if ':' in row[iD]:
                    is_concept = True
                if not is_concept:
                    cde_element = DugElement(
                        elem_id=row[iD],
                        name=row[name],
                        desc=row[name],
                        elem_type='CDE',
                        collection_id='',
                        collection_name=''
                    )
                    current_cdes.append(cde_element)
                else:
                    cde_element = DugConcept(
                        concept_id=row[iD],
                        name=row[name],
                        desc='',
                        concept_type='biolink:NameThing'
                    )
                    current_concepts.append(cde_element)
                    other_concepts.append(cde_element)
            for concept in current_concepts:
                if phenx_element:
                    phenx_element.concepts[concept.id] = concept
                    phenx_elements.append(phenx_element)
                if loinc_element:
                    loinc_element.concepts[concept.id] = concept
                    loinc_elements.append(loinc_element)
            for cde in current_cdes:
                for concept in current_concepts:
                    cde.concepts[concept.id] = concept
                cde_elements.append(cde)
        return phenx_elements + loinc_elements + cde_elements + other_concepts

#
# if __name__ == '__main__':
#     file_name = ''
#     elements = PhenXParser()(file_name)
#     print(elements)