from dug.core.parsers import BDCParser, HEALDDM2Parser
from tests.integration.conftest import TEST_DATA_DIR
from pathlib import Path

def test_bdc_parse_study_name_from_filename():
    parser = BDCParser()
    filename = "whatever/phs000166.v2.pht000700.v1.CAMP_CData.data_dict_2009_09_03.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "CAMP_CData"
    # test if version numbers are > 9
    filename = "whatever/phs000166.v23.pht000700.v13.CAMP_CData.data_dict_2009_09_03.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "CAMP_CData"

def test_bdc_parse_study_name_from_gap_exchange_file():
    parser = BDCParser()
    parse_filepath = Path(TEST_DATA_DIR / "phs001252.v1.p1" / "phs001252.v1.pht006366.v1.ECLIPSE_Subject.data_dict.xml")
    studyname = parser.parse_study_name_from_gap_exchange_file(parse_filepath)
    assert studyname == "Evaluation of COPD Longitudinally to Identify Predictive Surrogate Endpoints (ECLIPSE)"

def test_bdc_parser():
    parser = BDCParser()
    parse_file = str(TEST_DATA_DIR / "phs001252.v1.p1" / "phs001252.v1.pht006366.v1.ECLIPSE_Subject.data_dict.xml")
    elements = parser(parse_file)
    studies = [e for e in elements if e.type == 'study']
    assert len(studies) == 1
    assert studies[0].name == "Evaluation of COPD Longitudinally to Identify Predictive Surrogate Endpoints (ECLIPSE)"
    assert "dbGaP" in studies[0].programs
    variables = [e for e in elements if e.type == 'variable']
    assert len(variables) == 2
    for var in variables:
        assert studies[0].id in var.parents
        assert var.parent_type == "study"
        assert "dbGaP" in var.programs
  
def test_heal_cde_ddm2_parser():
    parser = HEALDDM2Parser()
    parse_file = str(TEST_DATA_DIR / "heal_cde_ddm2_gad2.dug.json")

    elements = parser(parse_file)
    sections = [k for k in elements if k.type == 'section']
    assert(len(sections) == 1)
    studies = [k for k in elements if k.type == 'study']
    assert(len(studies) == 0)
    variables = [k for k in elements if k.type == 'variable']
    assert(len(variables) > 0)

def test_heal_study_ddm2_parser():
    parser = HEALDDM2Parser()
    parse_file = str(TEST_DATA_DIR / "heal_study_ddm2_HDP00166.dug.json")

    elements = parser(parse_file)
    sections = [k for k in elements if k.type == 'section']
    assert(len(sections) == 0)
    studies = [k for k in elements if k.type == 'study']
    assert(len(studies) == 1)
    variables = [k for k in elements if k.type == 'variable']
    assert(len(variables) > 0)
    assert(studies[0].tags == [{"category":"Research Network", "value":"(JCOIN): Justice Community Opioid Innovation Network"}])