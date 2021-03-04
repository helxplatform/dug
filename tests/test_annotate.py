from copy import copy

import pytest

from dug.annotate import Identifier, Preprocessor


def test_identifier():

    ident_1 = Identifier(
        "PrimaryIdent:1", "first identifier", types=[], search_text="", description=""
    )

    assert "PrimaryIdent" == ident_1.id_type

    ident_2 = Identifier(
        "PrimaryIdent:1", "first identifier", types=[], search_text="", description=""
    )

    assert ident_1 == ident_2


@pytest.mark.parametrize(
    "preprocessor,input_text,expected_text",
    [
        (Preprocessor(), "Hello_world", "Hello world"),
        (Preprocessor({"Hello": "Hi"}, ["placeholder "]), "Hello placeholder world", "Hi world"),
    ]

)
def test_preprocessor_preprocess(preprocessor, input_text, expected_text):

    original_text = copy(input_text)
    output_text = preprocessor.preprocess(input_text)

    assert input_text == original_text  # Don't modify in-place
    assert output_text == expected_text