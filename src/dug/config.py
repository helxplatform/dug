import os

from dataclasses import dataclass, field


TRANQL_SOURCE: str = "redis:test"


@dataclass
class Config:
    """
    TODO: Make all URLs available as enviroment variables.
    """

    elastic_password: str = "changeme"
    redis_password: str = "changeme"

    elastic_host: str = "elasticsearch"
    elastic_port: int = 9200
    elastic_username: str = "elastic"
    elastic_scheme: str = "https"
    elastic_ca_path: str = ""
    elastic_ca_verify: bool = True
    max_ids_limit = 10000

    redis_host: str = "redis"
    redis_port: int = 6379

    nboost_host: str = "nboost"
    nboost_port: int = 8000

    studies_path: str=""

    kg_index_name: str="kg_index"
    concepts_index_name: str="concepts_index"
    variables_index_name: str='variables_index'
    studies_index_name: str='studies_index'
    sections_index_name: str='sections_index'

    # Preprocessor config that will be passed to annotate.Preprocessor constructor
    preprocessor: dict = field(
        default_factory=lambda: {
            "debreviator": {"BMI": "body mass index"},
            "stopwords": ["the"],
        }
    )
    annotator_type: str = "monarch"
    # Annotator config that will be passed to annotate.Annotator constructor
    annotator_args: dict = field(
        default_factory=lambda: {
            "monarch": {
                "url": "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content="
            },
            "sapbert": {
                "classification_url": "http://med-nemo-serve-nemo-web-server.ner/annotate/",
                "annotator_url": "http://qdrant-sapbert-nemo-web-server.ner/annotate/",
                "score_threshold": 0.8,
                "bagel": {
                    "enabled": False,
                    "url": "https://bagel.apps.renci.org/group_synonyms_openai",
                    "prompt": "bagel/ask_classes",
                    "llm_args": {
                        "llm_model_name": "gpt-4o-2024-05-13",
                        "organization": "",
                        "access_key": "",
                        "llm_model_args": {
                            "top_p": 0,
                            "temperature": 0.1
                        }
                    }
                }
            }
        }
    )

    # Normalizer config that will be passed to annotate.Normalizer constructor
    normalizer: dict = field(
        default_factory=lambda: {
            "url": "http://nn-web-node-normalization-web-service-root.translator-dev:8080/get_normalized_nodes?conflate=false&description=true&curie="
        }
    )

    # Synonym service config that will be passed to annotate.SynonymHelper constructor
    synonym_service: dict = field(
        default_factory=lambda: {
            "url": "http://name-resolution-name-lookup-web-svc.translator-dev:2433/synonyms"
        }
    )

    # Ontology metadata helper config that will be passed to annotate.OntologyHelper constructor
    ontology_helper: dict = field(
        default_factory=lambda: {
            "url": "https://api.monarchinitiative.org/api/bioentity/"
        }
    )

    # Redlist of identifiers not to expand via TranQL
    tranql_exclude_identifiers: list = field(default_factory=lambda: ["CHEBI:17336"])

    tranql_queries: dict = field(
        default_factory=lambda: {
            "disease": ["disease", "phenotypic_feature"],
            "pheno": ["phenotypic_feature", "disease"],
            "anat": ["disease", "anatomical_entity"],
            "chem_to_disease": ["chemical_entity", "disease"],
            "small_molecule_to_disease": ["small_molecule", "disease"],
            "chemical_mixture_to_disease": ["chemical_mixture", "disease"],
            "phen_to_anat": ["phenotypic_feature", "anatomical_entity"],
        }
    )

    node_to_element_queries: dict = field(
        default_factory=lambda: {
            # Dug element type to cast the query kg nodes to
            "cde": {
                # Parse nodes matching criteria in kg
                "node_type": "biolink:Publication",
                "curie_prefix": "HEALCDE",
                # list of attributes that are lists to be casted to strings
                "list_field_choose_first": ["files"],
                "attribute_mapping": {
                    # "DugElement Attribute" : "KG Node attribute"
                    "name": "name",
                    "desc": "summary",
                    "collection_name": "cde_category",
                    "collection_id": "cde_category",
                    "action": "files",
                },
            }
        }
    )

    concept_expander: dict = field(
        default_factory=lambda: {
            "url": "http://search-tranql:8081/tranql/tranql/query?dynamic_id_resolution=true&asynchronous=false",
            "min_tranql_score": 0.0,
        }
    )

    # List of ontology types that can be used even if they fail normalization
    ontology_greenlist: list = field(
        default_factory=lambda: [
            "PATO",
            "CHEBI",
            "MONDO",
            "UBERON",
            "HP",
            "MESH",
            "UMLS",
        ]
    )

    @classmethod
    def from_env(cls):
        env_vars = {
            "elastic_host": "ELASTIC_API_HOST",
            "elastic_port": "ELASTIC_API_PORT",
            "elastic_scheme": "ELASTIC_API_SCHEME",
            "elastic_ca_path": "ELASTIC_CA_PATH",
            "elastic_username": "ELASTIC_USERNAME",
            "elastic_password": "ELASTIC_PASSWORD",
            "elastic_ca_verify": "ELASTIC_CA_VERIFY",
            "redis_host": "REDIS_HOST",
            "redis_port": "REDIS_PORT",
            "redis_password": "REDIS_PASSWORD",
            "studies_path": "STUDIES_PATH",
            "kg_index_name": "ELASTIC_KG_INDEX_NAME",
            "concepts_index_name": "ELASTIC_CONCEPTS_INDEX_NAME",
            "variables_index_name": "ELASTIC_VARIABLES_INDEX_NAME",
            "studies_index_name": "ELASTIC_STUDIES_INDEX_NAME",
            "sections_index_name": "ELASTIC_SECTIONS_INDEX_NAME",
        }
        kwargs = {}
        for kwarg, env_var in env_vars.items():
            env_value = os.environ.get(env_var)
            if env_value:
                kwargs[kwarg] = env_value
                if kwarg in ['redis_port', 'elastic_port']:
                    kwargs[kwarg] = int(env_value)
                # default elastic verify cert to true
                if kwarg == "elastic_ca_verify":
                    kwargs[kwarg] = False if (env_value and env_value.lower() == "false") else True
        return cls(**kwargs)
