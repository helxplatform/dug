from dug.core.parsers import DbGaPParser, NIDAParser, TOPMedTagParser, SciCrunchParser, AnvilDbGaPParser,\
    CRDCDbGaPParser, KFDRCDbGaPParser, SPRINTParser
from tests.integration.conftest import TEST_DATA_DIR

def test_dbgap_parse_study_name_from_filename():
    parser = DbGaPParser()
    filename = "whatever/phs000166.v2.pht000700.v1.CAMP_CData.data_dict_2009_09_03.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "CAMP_CData"
    # test if version numbers are > 9
    filename = "whatever/phs000166.v23.pht000700.v13.CAMP_CData.data_dict_2009_09_03.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "CAMP_CData"

def test_nida_parse_study_name_from_filename():
    parser = NIDAParser()
    filename = "whatever/NIDA-CPU0008-Dictionary.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "NIDA-CPU0008"
    filename = "whatever/NIDA-CSP1019_DD.xml"
    studyname = parser.parse_study_name_from_filename(filename)
    assert studyname == "NIDA-CSP1019"

def test_dbgap_parser():
    parser = DbGaPParser()
    parse_file = str(TEST_DATA_DIR / "phs000166.v2.pht000700.v1.CAMP_CData.data_dict_2009_09_03.xml")
    elements = parser(parse_file)
    assert len(elements) > 0

def test_db_gap_scicrunch_parser():
    parser = SciCrunchParser()
    parse_file = str(TEST_DATA_DIR / "DOI:10.26275-0ce8-cuwi.xml")
    elements = parser(parse_file)
    assert len(elements) == 6
    for element in elements:
        assert element.collection_action == "https://DOI.org/10.26275/0ce8-cuwi"
        assert element.collection_name == "Identification of peripheral neural circuits that regulate heart rate using optogenetic and viral vector strategies"

    parse_file2 = str(TEST_DATA_DIR / "DOI:10.26275-zupz-yhtf.xml")
    elements2 = parser(parse_file2)
    assert len(elements2) == 1
    for element in elements2:
        assert element.collection_action == "https://DOI.org/10.26275/zupz-yhtf"
        assert element.collection_name == "Lower urinary tract nerve responses to high-density epidural sacral spinal cord stimulation"

    # the source SciCrunch file has some unicode characters. This test makes sure they have been succesfully
    # converted to utf8
    parse_file3 = str(TEST_DATA_DIR / "DOI:10.26275-c4xq-9kl0.xml")
    elements3 = parser(parse_file3)
    assert len(elements3) == 5
    for element in elements3:
        assert element.collection_action == "https://DOI.org/10.26275/c4xq-9kl0"
        assert element.collection_name == "Effect of Intermittent Hypoxia Preconditioning in Rats with Chronic Cervical Spinal Cord Injury – An electrophysiological Study"

def test_nida_parser():
    parser = NIDAParser()
    parse_file = str(TEST_DATA_DIR / "NIDA-CPU0008-Dictionary.xml")
    elements = parser(parse_file)
    assert len(elements) > 0

def test_topmed_tag_parser():
    parser = TOPMedTagParser()
    parse_file = str(TEST_DATA_DIR / "test_variables_v2.0.csv")
    elements = parser(parse_file)
    assert len(elements) == 62
    for element in elements:
        assert element.name != element.id
        assert element.description != element.id


def test_anvil_parser():
    parser = AnvilDbGaPParser()
    parse_file = str(TEST_DATA_DIR / "phs001547.v1.pht009987.v1.TOPMed_CCDG_GENAF_Subject.data_dict.xml")
    elements = parser(parse_file)
    assert len(elements) == 3
    for element in elements:
        assert element.type == "AnVIL"


def test_crdc_parser():
    parser = CRDCDbGaPParser()
    parse_file = str(TEST_DATA_DIR / "phs001547.v1.pht009987.v1.TOPMed_CCDG_GENAF_Subject.data_dict.xml")
    elements = parser(parse_file)
    assert len(elements) == 3
    for element in elements:
        assert element.type == "Cancer Data Commons"


def test_kfdrc_parser():
    parser = KFDRCDbGaPParser()
    parse_file = str(TEST_DATA_DIR / "phs001547.v1.pht009987.v1.TOPMed_CCDG_GENAF_Subject.data_dict.xml")
    elements = parser(parse_file)
    assert len(elements) == 3
    for element in elements:
        assert element.type == "Kids First"


def test_sprint_parser():
    parser = SPRINTParser()
    parse_file = str(TEST_DATA_DIR / "phs001547.v1.pht009987.v1.TOPMed_CCDG_GENAF_Subject.data_dict.xml")
    elements = parser(parse_file)
    assert len(elements) == 3
    for element in elements:
        assert element.type == "SPRINT"