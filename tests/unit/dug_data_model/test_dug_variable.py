# Tests for DugVariable.
import pytest

from dug_data_model.v2 import DugVariable

DUG_VARIABLE_EXPANSION_TEST_CASES = [
    ("variable_name", "variable name"),
    ("VariableName", "Variable Name"),
    ("AnotherVariableName", "Another Variable Name"),
    ("JSONVariable", "JSON Variable"),
    ("yet_another_variableName", "yet another variable Name"),
    ("variable_collection123", "variable collection 123"),
    ("vde_123def", "vde 123 def"),
]

@pytest.mark.parametrize("variable_name,expanded_name", DUG_VARIABLE_EXPANSION_TEST_CASES)
def test_dug_variable_expansion(variable_name, expanded_name):
    """
    DugVariable.ml_ready_desc should be able to identify variables in CamelCase and snake_case
    and expand both of them to simplify NER.
    """

    var = DugVariable(id="var", name=variable_name, description="some desc")
    expected_ml_ready_desc = f"{variable_name} ({expanded_name}): some desc"
    assert var.ml_ready_desc == expected_ml_ready_desc


def test_dug_variable_no_expansion():
    """
    ml_ready_desc should not include a cleaned up variable if the variable name is neither in CamelCase nor snake_case.
    """

    assert DugVariable(id="var", name="123", description="some desc").ml_ready_desc == "123: some desc"
    assert DugVariable(id="var", name="variablename", description="some desc").ml_ready_desc == "variablename: some desc"
