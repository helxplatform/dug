"Unit tests for the async_search module"

import asyncio
import json
from importlib import reload
from unittest import TestCase, mock
from fastapi.testclient import TestClient

from dug.core import async_search
from dug.config import Config

async def _mock_search(*args, **kwargs):
    "Mock of elasticsearch search function. Ignores argument"
    return _brain_search_result()

async def _mock_count(*args, **kwargs):
    "Mock of elasticsearch count function. Ignores argument"
    return {'count': 90, '_shards': {'total': 1, 'successful': 1,
                                     'skipped': 0, 'failed': 0}}
es_mock = mock.AsyncMock()
es_mock.search = _mock_search
es_mock.count = _mock_count

class SearchTestCase(TestCase):
    "Mocked unit tests for async_search"

    def setUp(self):
        "Build mock elasticsearch responses"
        search_result = _brain_search_result()
        self.search = async_search.Search(Config.from_env())
        self.query_body = self.search._get_concepts_query("brain")
        self.search.es = es_mock

    def test_concepts_search(self):
        "Test async_search concepts search"
        result = asyncio.run(
            self.search.search_concepts("brain"))
        self.assertIn('total_items', result)
        self.assertEqual(result['total_items'], 90)
        self.assertIn('concept_types', result)
        self.assertIsInstance(result['concept_types'], dict)
        self.assertEqual(len(result['concept_types']), 9)
        self.assertEqual(result['concept_types']['anatomical entity'], 10)


brain_result_json = """{
  "hits": {
    "hits": [
      {
        "_type": "_doc",
        "_id": "MONDO:0005560",
        "_score": 274.8391,
        "_source": {
          "id": "MONDO:0005560",
          "name": "brain disease",
          "description": "A disease affecting the brain or part of the brain.",
          "type": "disease",
          "search_terms": [
            "brain disease",
            "disorder of brain",
            "disease of brain",
            "disease or disorder of brain",
            "brain disease or disorder"
          ],
          "optional_terms": [
            "alcohol use disorder measurement",
            "GBA carrier status",
            "systemising measurement",
            "Abnormal nervous system physiology",
            "Hypoglycemic encephalopathy",
            "Nervous System Part",
            "linguistic error measurement",
            "Brain abscess",
            "anatomical entity",
            "Phenotypic abnormality",
            "time to first cigarette measurement",
            "Progressive encephalopathy",
            "Epileptic encephalopathy",
            "Necrotizing encephalopathy",
            "Recurrent encephalopathy",
            "alcohol dependence measurement",
            "brain disease",
            "cognitive inhibition measurement",
            "Mitochondrial encephalopathy",
            "Chronic hepatic encephalopathy",
            "cocaine use measurement",
            "Nonprogressive encephalopathy",
            "Profound static encephalopathy",
            "Brain",
            "Acute encephalopathy",
            "ADHD symptom measurement",
            "cannabis dependence measurement",
            "Infantile encephalopathy",
            "opioid overdose severity measurement",
            "delayed reward discounting measurement",
            "attention function measurement",
            "Herpes simplex encephalitis",
            "Abnormality of neuronal migration",
            "Acute necrotizing encephalopathy",
            "Congenital encephalopathy",
            "vascular brain injury measurement",
            "Primary microcephaly",
            "Central Nervous System Part",
            "executive function measurement",
            "syntactic complexity measurement"
          ],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0005560",
              "label": "brain disease",
              "equivalent_identifiers": [
                "MONDO:0005560",
                "DOID:936",
                "UMLS:C0006111",
                "UMLS:C0085584",
                "MESH:D001927",
                "MEDDRA:10006120",
                "MEDDRA:10014623",
                "MEDDRA:10014625",
                "MEDDRA:10014636",
                "MEDDRA:10014641",
                "NCIT:C26920",
                "NCIT:C96413",
                "SNOMEDCT:81308009",
                "ICD10:G93.40",
                "ICD10:G93.9",
                "ICD9:348.30",
                "ICD9:348.9",
                "HP:0001298"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": [
                "brain disease",
                "brain disease or disorder",
                "disease of brain",
                "disease or disorder of brain",
                "disorder of brain"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "MONDO:0005394",
        "_score": 253.45584,
        "_source": {
          "id": "MONDO:0005394",
          "name": "brain infarction",
          "description": "Tissue necrosis in any area of the brain, including the cerebral hemispheres, the cerebellum, and the brain stem. Brain infarction is the result of a cascade of events initiated by inadequate blood flow through the brain that is followed by hypoxia and hypoglycemia in brain tissue. Damage may be temporary, permanent, selective or pan-necrosis.",
          "type": "disease",
          "search_terms": [
            "BRAIN INFARCTION"
          ],
          "optional_terms": [
            "blood vasculature",
            "brain infarction"
          ],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0005394",
              "label": "brain infarction",
              "equivalent_identifiers": [
                "MONDO:0005394",
                "DOID:3454",
                "UMLS:C0751955",
                "MESH:D020520",
                "MEDDRA:10072154"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": []
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "UBERON:0000955",
        "_score": 252.57217,
        "_source": {
          "id": "UBERON:0000955",
          "name": "brain",
          "description": "The brain is the center of the nervous system in all vertebrate, and most invertebrate, animals. Some primitive animals such as jellyfish and starfish have a decentralized nervous system without a brain, while sponges lack any nervous system at all. In vertebrates, the brain is located in the head, protected by the skull and close to the primary sensory apparatus of vision, hearing, balance, taste, and smell[WP].",
          "type": "anatomical entity",
          "search_terms": [
            "the brain",
            "suprasegmental levels of nervous system",
            "brain",
            "suprasegmental structures",
            "synganglion",
            "encephalon"
          ],
          "optional_terms": [],
          "concept_action": "",
          "identifiers": [
            {
              "id": "UBERON:0000955",
              "label": "brain",
              "equivalent_identifiers": [
                "UBERON:0000955"
              ],
              "type": [
                "biolink:GrossAnatomicalStructure",
                "biolink:AnatomicalEntity",
                "biolink:OrganismalEntity",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon",
                "biolink:PhysicalEssence",
                "biolink:PhysicalEssenceOrOccurrent"
              ],
              "synonyms": [
                "encephalon",
                "suprasegmental levels of nervous system",
                "suprasegmental structures",
                "synganglion",
                "the brain"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "MONDO:0017998",
        "_score": 136.03186,
        "_source": {
          "id": "MONDO:0017998",
          "name": "PLA2G6-associated neurodegeneration",
          "description": "Any neurodegeneration with brain iron accumulation in which the cause of the disease is a mutation in the PLA2G6 gene.",
          "type": "disease",
          "search_terms": [
            "plans",
            "neurodegeneration with brain iron accumulation caused by mutation in PLA2G6",
            "PLA2G6 neurodegeneration with brain iron accumulation",
            "PLAN"
          ],
          "optional_terms": [],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0017998",
              "label": "PLA2G6-associated neurodegeneration",
              "equivalent_identifiers": [
                "MONDO:0017998",
                "ORPHANET:329303"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": [
                "neurodegeneration with brain iron accumulation caused by mutation in PLA2G6",
                "PLA2G6 neurodegeneration with brain iron accumulation",
                "PLAN"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "MONDO:0002679",
        "_score": 128.80138,
        "_source": {
          "id": "MONDO:0002679",
          "name": "cerebral infarction",
          "description": "An ischemic condition of the brain, producing a persistent focal neurological deficit in the area of distribution of the cerebral arteries.",
          "type": "disease",
          "search_terms": [
            "cerebral infarct",
            "infarction, cerebral",
            "cerebral infarction",
            "CVA - cerebral infarction",
            "cerebral ischemia",
            "brain infarction of telencephalon",
            "telencephalon brain infarction",
            "cerebral, infarction"
          ],
          "optional_terms": [
            "Abnormal nervous system morphology",
            "structure with developmental contribution from neural crest",
            "stroke outcome severity measurement",
            "brain infarction of telencephalon",
            "Phenotypic abnormality",
            "cerebral, infarction",
            "cerebral infarct",
            "Abnormal arterial physiology",
            "CVA - cerebral infarction",
            "telencephalon brain infarction",
            "Abnormality of brain morphology",
            "Tissue ischemia",
            "cerebral infarction",
            "Pontine ischemic lacunes",
            "cerebral ischemia",
            "Abnormal vascular morphology",
            "Lacunar stroke",
            "Abnormality of the vasculature",
            "Abnormal cerebral vascular morphology",
            "Abnormal vascular physiology",
            "infarction, cerebral",
            "Abnormal cardiovascular system physiology",
            "Abnormality of cardiovascular system morphology"
          ],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0002679",
              "label": "cerebral infarction",
              "equivalent_identifiers": [
                "MONDO:0002679",
                "DOID:3526",
                "OMIM:601367",
                "UMLS:C0007785",
                "UMLS:C0948008",
                "MESH:D000083242",
                "MESH:D002544",
                "MEDDRA:10008117",
                "MEDDRA:10008118",
                "MEDDRA:10021755",
                "MEDDRA:10023027",
                "MEDDRA:10055221",
                "MEDDRA:10061256",
                "NCIT:C50486",
                "NCIT:C95802",
                "SNOMEDCT:422504002",
                "SNOMEDCT:432504007",
                "ICD10:I63",
                "HP:0002140"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": [
                "brain infarction of telencephalon",
                "cerebral infarct",
                "cerebral infarction",
                "cerebral ischemia",
                "cerebral, infarction",
                "CVA - cerebral infarction",
                "infarction, cerebral",
                "telencephalon brain infarction"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "UBERON:6110636",
        "_score": 120.47298,
        "_source": {
          "id": "UBERON:6110636",
          "name": "insect adult cerebral ganglion",
          "description": "The pre-oral neuropils of the adult brain located above, around and partially below the esophagus, including the optic lobes. It excludes the gnathal ganglion. Developmentally, it comprises three fused neuromeres: protocerebrum, deutocerebrum, and tritocerebrum.",
          "type": "anatomical entity",
          "search_terms": [
            "supraesophageal ganglion",
            "SPG",
            "cerebrum",
            "brain",
            "CRG"
          ],
          "optional_terms": [],
          "concept_action": "",
          "identifiers": [
            {
              "id": "UBERON:6110636",
              "label": "insect adult cerebral ganglion",
              "equivalent_identifiers": [
                "UBERON:6110636"
              ],
              "type": [
                "biolink:GrossAnatomicalStructure",
                "biolink:AnatomicalEntity",
                "biolink:OrganismalEntity",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon",
                "biolink:PhysicalEssence",
                "biolink:PhysicalEssenceOrOccurrent"
              ],
              "synonyms": [
                "CRG",
                "SPG",
                "brain",
                "cerebrum",
                "supraesophageal ganglion"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "MONDO:0045057",
        "_score": 115.8625,
        "_source": {
          "id": "MONDO:0045057",
          "name": "delirium",
          "description": "A disorder characterized by confusion; inattentiveness; disorientation; illusions; hallucinations; agitation; and in some instances autonomic nervous system overactivity. It may result from toxic/metabolic conditions or structural brain lesions. (From Adams et al., Principles of Neurology, 6th ed, pp411-2)",
          "type": "disease",
          "search_terms": [
            "delirium",
            "OBS syndrome",
            "organic brain syndrome"
          ],
          "optional_terms": [
            "Confusion",
            "Abnormality of higher mental function",
            "Abnormal nervous system physiology",
            "delirium",
            "Reduced consciousness/confusion",
            "Phenotypic abnormality"
          ],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0045057",
              "label": "delirium",
              "equivalent_identifiers": [
                "MONDO:0045057",
                "UMLS:C0011206",
                "UMLS:C0029221",
                "UMLS:C1285577",
                "UMLS:C1306588",
                "MESH:D003693",
                "MEDDRA:10000685",
                "MEDDRA:10000693",
                "MEDDRA:10000694",
                "MEDDRA:10000702",
                "MEDDRA:10006150",
                "MEDDRA:10012217",
                "MEDDRA:10012218",
                "MEDDRA:10012219",
                "MEDDRA:10031077",
                "MEDDRA:10042790",
                "NCIT:C2981",
                "NCIT:C34868",
                "SNOMEDCT:130987000",
                "SNOMEDCT:2776000",
                "SNOMEDCT:419567006",
                "HP:0031258"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": [
                "OBS syndrome",
                "organic brain syndrome"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "UBERON:0002298",
        "_score": 90.43253,
        "_source": {
          "id": "UBERON:0002298",
          "name": "brainstem",
          "description": "Stalk-like part of the brain that includes amongst its parts the medulla oblongata of the hindbrain and the tegmentum of the midbrain[ZFA,MP,generalized].",
          "type": "anatomical entity",
          "search_terms": [
            "truncus encephalicus",
            "truncus encephali",
            "lamella pallidi incompleta",
            "accessory medullary lamina of pallidum",
            "lamina pallidi incompleta",
            "lamina medullaris incompleta pallidi",
            "brain stem",
            "brainstem",
            "lamina medullaris accessoria"
          ],
          "optional_terms": [],
          "concept_action": "",
          "identifiers": [
            {
              "id": "UBERON:0002298",
              "label": "brainstem",
              "equivalent_identifiers": [
                "UBERON:0002298",
                "UMLS:C0006121",
                "NCIT:C12441"
              ],
              "type": [
                "biolink:GrossAnatomicalStructure",
                "biolink:AnatomicalEntity",
                "biolink:OrganismalEntity",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon",
                "biolink:PhysicalEssence",
                "biolink:PhysicalEssenceOrOccurrent"
              ],
              "synonyms": [
                "brain stem",
                "truncus encephali",
                "accessory medullary lamina of pallidum",
                "lamella pallidi incompleta",
                "lamina medullaris accessoria",
                "lamina medullaris incompleta pallidi",
                "lamina pallidi incompleta",
                "truncus encephalicus"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "UBERON:0001894",
        "_score": 73.00175,
        "_source": {
          "id": "UBERON:0001894",
          "name": "diencephalon",
          "description": "The division of the forebrain that develops from the foremost primary cerebral vesicle.",
          "type": "anatomical entity",
          "search_terms": [
            "mature diencephalon",
            "thalamencephalon",
            "between brain",
            "interbrain",
            "betweenbrain",
            "diencephalon",
            "died."
          ],
          "optional_terms": [],
          "concept_action": "",
          "identifiers": [
            {
              "id": "UBERON:0001894",
              "label": "diencephalon",
              "equivalent_identifiers": [
                "UBERON:0001894",
                "UMLS:C0012144"
              ],
              "type": [
                "biolink:GrossAnatomicalStructure",
                "biolink:AnatomicalEntity",
                "biolink:OrganismalEntity",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon",
                "biolink:PhysicalEssence",
                "biolink:PhysicalEssenceOrOccurrent"
              ],
              "synonyms": [
                "between brain",
                "interbrain",
                "mature diencephalon",
                "thalamencephalon",
                "diencephalon",
                "betweenbrain"
              ]
            }
          ]
        }
      },
      {
        "_type": "_doc",
        "_id": "MONDO:0013792",
        "_score": 69.71182,
        "_source": {
          "id": "MONDO:0013792",
          "name": "intracerebral hemorrhage",
          "description": "Bleeding into one or both cerebral hemispheres including the basal ganglia and the cerebral cortex. It is often associated with hypertension and craniocerebral trauma.",
          "type": "disease",
          "search_terms": [
            "stroke, hemorrhagic",
            "'bleeding in brain'",
            "hemorrhage, intracerebral, susceptibility to",
            "ich",
            "stroke, hemorrhagic, susceptibility to"
          ],
          "optional_terms": [
            "Abnormality of the musculoskeletal system",
            "Abnormal nervous system morphology",
            "Abnormality of head or neck",
            "Recurrent cerebral hemorrhage",
            "Intraventricular hemorrhage",
            "Phenotypic abnormality",
            "Grade I preterm intraventricular hemorrhage",
            "stroke, hemorrhagic, susceptibility to",
            "Hemorrhage",
            "Intraventricular Hemorrhage Related to Birth",
            "intracerebral hemorrhage",
            "Antenatal intracerebral hemorrhage",
            "Periventricular Hemorrhage of the Newborn",
            "stroke, hemorrhagic",
            "ich",
            "Abnormal bleeding",
            "Abnormality of brain morphology",
            "Internal hemorrhage",
            "Cerebral Hemorrhage Related to Birth",
            "Finding",
            "Abnormality of the skeletal system",
            "Intraparenchymal Hemorrhage of the Newborn",
            "Abnormal vascular morphology",
            "Abnormality of the vasculature",
            "Abnormal cerebral vascular morphology",
            "Finding by Cause",
            "Abnormality of the head",
            "Abnormality of cardiovascular system morphology",
            "Intraventricular Hemorrhage with Parenchymal Hemorrhage of the Newborn",
            "Abnormal cardiovascular system physiology",
            "Abnormality of blood circulation",
            "hemorrhage, intracerebral, susceptibility to"
          ],
          "concept_action": "",
          "identifiers": [
            {
              "id": "MONDO:0013792",
              "label": "intracerebral hemorrhage",
              "equivalent_identifiers": [
                "MONDO:0013792",
                "OMIM:614519",
                "UMLS:C0472369",
                "UMLS:C0553692",
                "UMLS:C1862876",
                "UMLS:C2937358",
                "UMLS:C3281105",
                "UMLS:C5234922",
                "MESH:D000083302",
                "MESH:D002543",
                "MEDDRA:10008111",
                "MEDDRA:10008114",
                "MEDDRA:10018972",
                "MEDDRA:10019005",
                "MEDDRA:10019016",
                "MEDDRA:10019529",
                "MEDDRA:10019531",
                "MEDDRA:10019551",
                "MEDDRA:10022737",
                "MEDDRA:10022751",
                "MEDDRA:10022753",
                "MEDDRA:10022754",
                "MEDDRA:10048863",
                "MEDDRA:10055278",
                "MEDDRA:10055293",
                "MEDDRA:10055800",
                "MEDDRA:10055815",
                "MEDDRA:10071793",
                "MEDDRA:10077620",
                "MEDDRA:10077622",
                "NCIT:C50485",
                "NCIT:C95803",
                "SNOMEDCT:230706003",
                "SNOMEDCT:274100004",
                "HP:0001342"
              ],
              "type": [
                "biolink:Disease",
                "biolink:DiseaseOrPhenotypicFeature",
                "biolink:BiologicalEntity",
                "biolink:NamedThing",
                "biolink:Entity",
                "biolink:ThingWithTaxon"
              ],
              "synonyms": [
                "stroke, hemorrhagic",
                "hemorrhage, intracerebral, susceptibility to",
                "ich",
                "stroke, hemorrhagic, susceptibility to"
              ]
            }
          ]
        }
      }
    ]
  },
  "aggregations": {
    "type-count": {
      "doc_count_error_upper_bound": 0,
      "sum_other_doc_count": 0,
      "buckets": [
        {
          "key": "phenotype",
          "doc_count": 36
        },
        {
          "key": "disease",
          "doc_count": 28
        },
        {
          "key": "anatomical entity",
          "doc_count": 10
        },
        {
          "key": "TOPMed Phenotype Concept",
          "doc_count": 8
        },
        {
          "key": "drug",
          "doc_count": 3
        },
        {
          "key": "",
          "doc_count": 2
        },
        {
          "key": "biological process",
          "doc_count": 1
        },
        {
          "key": "clinical_course",
          "doc_count": 1
        },
        {
          "key": "molecular entity",
          "doc_count": 1
        }
      ]
    }
  }
}
"""

def _brain_search_result():
    """Stuck in a function just so I can shove it down here at the end
    of the test module"""
    return json.loads(brain_result_json)
