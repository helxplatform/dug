import os
import dug.tranql as tql

# Redis cache config
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', 6379)
redis_password = os.environ.get('REDIS_PASSWORD', '')

# ElasticSearch config options
elasticsearch_host = os.environ.get('ELASTIC_API_HOST', 'localhost')
elasticsearch_port = os.environ.get('ELASTIC_API_PORT', 9200)

# Preprocessor config that will be passed to annotate.Preprocessor constructor
preprocessor = {
    "debreviator": {
        "BMI": "body mass index"
    },
    "stopwords": ["the"]
}

# Annotator config that will be passed to annotate.Annotator constructor
annotator = {
    'url': "https://api.monarchinitiative.org/api/nlp/annotate/entities?min_length=4&longest_only=false&include_abbreviation=false&include_acronym=false&include_numbers=false&content="
}

# Normalizer config that will be passed to annotate.Normalizer constructor
normalizer = {
    'url': "https://nodenormalization-sri.renci.org/get_normalized_nodes?curie="
}

# Synonym service config that will be passed to annotate.SynonymHelper constructor
synonym_service = {
    'url': "https://onto.renci.org/synonyms/"
}

# Ontology metadata helper config that will be passed to annotate.OntologyHelper constructor
ontology_helper = {
    'url': "https://api.monarchinitiative.org/api/bioentity/"
}

# Redlist of identifiers not to expand via TranQL
tranql_exclude_identifiers = ["CHEBI:17336"]

# TranQL queries used to expand identifiers
tranql_source = "/graph/gamma/quick"
tranql_queries = {
    "disease": tql.QueryFactory(["disease", "phenotypic_feature"], tranql_source),
    "pheno": tql.QueryFactory(["phenotypic_feature", "disease"], tranql_source),
    "anat": tql.QueryFactory(["disease", "anatomical_entity"], tranql_source),
    "chem_to_disease": tql.QueryFactory(["chemical_substance", "disease"], tranql_source),
    "phen_to_anat": tql.QueryFactory(["phenotypic_feature", "anatomical_entity"], tranql_source),
    #"anat_to_disease": tql.QueryFactory(["anatomical_entity", "disease"], tranql_source),
    #"anat_to_pheno": tql.QueryFactory(["anatomical_entity", "phenotypic_feature"], tranql_source)
}

concept_expander = {
    'url': "https://tranql.renci.org/tranql/query?dynamic_id_resolution=true&asynchronous=false",
    'min_tranql_score': 0.0
}

# List of ontology types that can be used even if they fail normalization
ontology_greenlist = ["PATO", "CHEBI", "MONDO", "UBERON", "HP", "MESH", "UMLS"]
