from dataclasses import dataclass, field


@dataclass
class MockConfig:

    # Preprocessor config that will be passed to annotate.Preprocessor constructor
    preprocessor: dict = field(default_factory=lambda: {
        "debreviator": {
            "BMI": "body mass index"
        },
        "stopwords": ["the"]
    })

    # Annotator config that will be passed to annotate.Annotator constructor
    annotator_type: str = "monarch"

    annotator_args: dict = field(
        default_factory=lambda: {
            "monarch": {
                "url": "http://annotator.api/?content="
            },
            "sapbert": {
                "classification_url": "http://classifier.api/annotate/",
                "annotator_url": "http://entity-link.api/annotate/",
            },
        }
    )

    # Normalizer config that will be passed to annotate.Normalizer constructor
    normalizer: dict = field(default_factory=lambda: {
        "url": "http://normalizer.api/?curie="
    })

    # Synonym service config that will be passed to annotate.SynonymHelper constructor
    synonym_service: dict = field(default_factory=lambda: {
        "url": "http://synonyms.api"
    })

    @classmethod
    def test_from_env(cls):
        kwargs = {}
        return cls(**kwargs)