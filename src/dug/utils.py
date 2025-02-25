import re
import bmt

bmt_tk = bmt.Toolkit()

class ObjectFactory:
    def __init__(self):
        self._builders = {}

    def register_builder(self, key, builder):
        self._builders[key] = builder

    def create(self, key, **kwargs):
        builder = self._builders.get(key)
        if not builder:
            raise ValueError(key)
        return builder(**kwargs)

    def get_builder_types(self):
        return list(self._builders.keys())


def complex_handler(obj):
    if hasattr(obj, 'jsonable'):
        return obj.jsonable()
    else:
        raise TypeError(f'Object of type {type(obj)} with value of {type(obj)} is not JSON serializable')


def get_dbgap_var_link(study_id, variable_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/variable.cgi"
    return f'{base_url}?study_id={study_id}&phv={variable_id}'


def get_dbgap_study_link(study_id):
    base_url = "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi"
    return f'{base_url}?study_id={study_id}'

def get_nida_study_link(study_id):
    base_url = "https://datashare.nida.nih.gov/study"
    return f'{base_url}/{study_id}'

def get_heal_platform_link(study_id):
    base_url = "https://healdata.org/portal/discovery"
    accession = study_id.split(':')[1]
    return f'{base_url}/{accession}'

def get_ctn_link(study_id):
    base_url = "https://ctnlibrary.org/protocol"
    accession = study_id.split(':')[1]
    return f'{base_url}/{accession}'

def biolink_snake_case(arg):
    """Convert such SnakeCase to snake_case.
       Non-alphanumeric characters are replaced with _.
       CamelCase is replaced with snake_case.
    """
    # replace non-alphanumeric characters with _
    tmp = re.sub(r'\W', '_', arg)
    # replace X with _x
    tmp = re.sub(
        r'(?<=[a-z])[A-Z](?=[a-z])',
        lambda c: '_' + c.group(0).lower(),
        tmp
    )
    # lower-case first character
    tmp = re.sub(
        r'^[A-Z](?=[a-z])',
        lambda c: c.group(0).lower(),
        tmp
    )
    return tmp

def get_formatted_biolink_name(bl_type):
    category = bl_type
    if isinstance(bl_type, str):
        bl_element = bmt_tk.get_element(bl_type)
        category = bl_element.class_uri or bl_element.slot_uri
    if isinstance(bl_type, list):
        return get_formatted_biolink_name(bl_type[0])
    return category