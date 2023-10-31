from copy import copy
from typing import List
from attr import field

import pytest
from dug.core.annotators.utils.biolink_purl_util import BioLinkPURLerizer


from tests.integration.mocks.mock_config import MockConfig
from dug.core.annotators import (
    DugIdentifier,
    AnnotateMonarch,
    DefaultNormalizer,
    DefaultSynonymFinder
)

def test_monarch_annotation_full(monarch_annotator_api, normalizer_api, null_normalizer_api, synonym_api, null_synonym_api):
    cfg = MockConfig.test_from_env()
    normalizer = DefaultNormalizer(**cfg.normalizer)
    synonym_finder = DefaultSynonymFinder(**cfg.synonym_service)

    annotator = AnnotateMonarch(
        normalizer=normalizer, synonym_finder=synonym_finder, config=cfg
    )
    input_text = "heart attack"

    text = annotator.preprocess_text(input_text)

    # Fetch identifiers
    raw_identifiers: List[DugIdentifier]  = annotator.annotate_text(text, monarch_annotator_api)

    processed_identifiers: List[DugIdentifier] = []
    for identifier in raw_identifiers:
        if identifier.id == "UBERON:0007100":
            # Perform normal normalization
            output = annotator.normalizer(identifier, normalizer_api)
            
            assert isinstance(output, DugIdentifier)
            assert output.id == 'UBERON:0007100'
            assert output.label == "primary circulatory organ"
            assert output.equivalent_identifiers == ['UBERON:0007100']
            assert output.types == 'anatomical entity'
        else:
            # act as if this is null
            output = annotator.normalizer(identifier, null_normalizer_api)

        # Should be returning normalized identifier for each identifier passed in
        if output is None:
            output = identifier
            # Test normalizer when null
            assert output.id == 'XAO:0000336'
            assert output.label == "heart primordium"

        # Add synonyms to identifier
        if identifier.id == "UBERON:0007100":
            output.synonyms = annotator.synonym_finder(output.id, synonym_api)
            assert output.synonyms == [
                    "primary circulatory organ",
                    "dorsal tube",
                    "adult heart",
                    "heart"
            ]
        else:
            output.synonyms = annotator.synonym_finder(output.id, null_synonym_api)
            assert output.synonyms == []
        # Get pURL for ontology identifer for more info
        output.purl = BioLinkPURLerizer.get_curie_purl(output.id)
        processed_identifiers.append(output)
    
    assert isinstance(processed_identifiers, List)
    assert len(processed_identifiers) == 2
    assert isinstance(processed_identifiers[0], DugIdentifier)