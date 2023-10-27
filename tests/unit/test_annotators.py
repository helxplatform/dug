from copy import copy
from typing import List

import pytest

from dug.config import Config
from dug.core.annotators import ( DugIdentifier, 
                                 AnnotateMonarch, 
                                 PreprocessorMonarch, 
                                 AnnotatorMonarch, 
                                 NormalizerMonarch, 
                                 SynonymFinderMonarch
                                 )
from unittest.mock import MagicMock

def test_identifier():
    ident_1 = DugIdentifier(
        "PrimaryIdent:1", "first identifier", types=[], search_text="", description=""
    )

    assert "PrimaryIdent" == ident_1.id_type

def test_monarch_annotator():
    cfg = Config.from_env()
    url = cfg.annotator["url"]
    preprocessor = PreprocessorMonarch(**cfg.preprocessor)
    annotator = AnnotatorMonarch(**cfg.annotator)
    normalizer = NormalizerMonarch(**cfg.normalizer)
    synonym_finder = SynonymFinderMonarch(**cfg.synonym_service)

    annotator = AnnotateMonarch(
        preprocessor=preprocessor,
        annotator=annotator,
        normalizer=normalizer,
        synonym_finder=synonym_finder
    )
    # annotator = AnnotateMonarch()
    assert annotator.annotate(text="Lama", http_session = MagicMock()) == url

# @pytest.mark.parametrize(
#     "preprocessor,input_text,expected_text",
#     [
#         (Preprocessor(), "Hello_world", "Hello world"),
#         (Preprocessor({"Hello": "Hi"}, ["placeholder"]), "Hello placeholder world", "Hi world"),
#     ]
# )
# def test_preprocessor_preprocess(preprocessor, input_text, expected_text):
#     original_text = copy(input_text)
#     output_text = preprocessor.preprocess(input_text)

#     assert input_text == original_text  # Don't modify in-place
#     assert output_text == expected_text


# def test_annotator_init():
#     cfg = Config.from_env()
#     url = cfg.annotator["url"]

#     annotator = Annotator(**cfg.annotator)
#     assert annotator.url == url


# def test_annotator_handle_response():
#     annotator = Annotator('foo')

#     response = {
#             "content": "heart attack",
#             "spans": [
#                 {
#                     "start": 0,
#                     "end": 5,
#                     "text": "heart",
#                     "token": [
#                         {
#                             "id": "UBERON:0015230",
#                             "category": [
#                                 "anatomical entity"
#                             ],
#                             "terms": [
#                                 "dorsal vessel heart"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 5,
#                     "text": "heart",
#                     "token": [
#                         {
#                             "id": "UBERON:0007100",
#                             "category": [
#                                 "anatomical entity"
#                             ],
#                             "terms": [
#                                 "primary circulatory organ"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 5,
#                     "text": "heart",
#                     "token": [
#                         {
#                             "id": "UBERON:0015228",
#                             "category": [
#                                 "anatomical entity"
#                             ],
#                             "terms": [
#                                 "circulatory organ"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 5,
#                     "text": "heart",
#                     "token": [
#                         {
#                             "id": "ZFA:0000114",
#                             "category": [
#                                 "anatomical entity"
#                             ],
#                             "terms": [
#                                 "heart"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 5,
#                     "text": "heart",
#                     "token": [
#                         {
#                             "id": "UBERON:0000948",
#                             "category": [
#                                 "anatomical entity"
#                             ],
#                             "terms": [
#                                 "heart"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 12,
#                     "text": "heart attack",
#                     "token": [
#                         {
#                             "id": "MONDO:0005068",
#                             "category": [
#                                 "disease"
#                             ],
#                             "terms": [
#                                 "myocardial infarction (disease)"
#                             ]
#                         }
#                     ]
#                 },
#                 {
#                     "start": 0,
#                     "end": 12,
#                     "text": "heart attack",
#                     "token": [
#                         {
#                             "id": "HP:0001658",
#                             "category": [
#                                 "phenotype",
#                                 "quality"
#                             ],
#                             "terms": [
#                                 "Myocardial infarction"
#                             ]
#                         }
#                     ]
#                 }
#             ]
#         }

#     identifiers: List[DugIdentifier] = annotator.handle_response(None, response)

#     assert len(identifiers) == 7
#     assert isinstance(identifiers[0], DugIdentifier)


# def test_annotator_call(annotator_api):
#     url = "http://annotator.api/?content="

#     annotator = Annotator(url)

#     text = "heart attack"
#     identifiers: List[DugIdentifier] = annotator.annotate(text, annotator_api)

#     assert len(identifiers) == 7
#     assert isinstance(identifiers[0], DugIdentifier)


# def test_normalizer(normalizer_api):
#     url = "http://normalizer.api/?curie="

#     identifier = DugIdentifier(
#         "UBERON:0007100",
#         label='primary circulatory organ',
#         types=['anatomical entity'],
#         description="",
#         search_text=['heart'],
#     )

#     normalizer = Normalizer(url)
#     output = normalizer.normalize(identifier, normalizer_api)
#     assert isinstance(output, DugIdentifier)
#     assert output.id == 'UBERON:0007100'
#     assert output.label == "primary circulatory organ"
#     assert output.equivalent_identifiers == ['UBERON:0007100']
#     assert output.types == 'anatomical entity'
    


# def test_synonym_finder(synonym_api):
#     curie = "UBERON:0007100"
#     url = f"http://synonyms.api"
#     finder = SynonymFinder(url)
#     result = finder.get_synonyms(
#         curie,
#         synonym_api,
#     )
#     assert result == [
#             "primary circulatory organ",
#             "dorsal tube",
#             "adult heart",
#             "heart"
#         ]





# def test_yield_partial_text():
#     annotator = Annotator('foo')
#     # text contains 800 characters + 9 new lines
#     text = """COG Protocol number on which the patient was enrolled [901=Trial of mouse monoclonal Anti-GD-2 antibody 14.G2A plus IL-2 with or without GM-CSF in children with refractory NBL or melanoma; 911=I-131-MIBG for therapy of advanced neuroblastoma; 914=A dose escalation study of cisplatin, doxorubicin, VP-16, and ifosfamide followed by GM-CSF in advanced NBL and peripheral neuroepithelioma; 925=Study of topotecan; 935=Study of ch14.18 with GM-CSF in children with NBL and other GD2 positive malignancies immediately post ABMT or PBSC; 937=Phase I trial of ZD1694, an inhibitor of thymidylate synthase, in pediatric patients with advanced neoplastic disease; 9709=A phase I study of fenretinide in children with high risk solid tumors; 321P2=New intensive chemotherapy for CCG stage II (with N-myc amplification), stage III and stage IV neuroblastoma; 321P3=Treatment of poor prognosis neuroblastoma before disease progression with intensive multimodal therapy and BMT; 323P=Cyclic combination chemotherapy for newly diagnosed stage III neuroblastoma age 2 and older and stage IV Nneuroblastoma all ages; 3881=Biology and therapy of good, intermediate, and selected poor prognosis neuroblastoma; 3891=Conventional dose chemoradiotherapy vs ablative chemoradiotherapy with autologous BMT for high-risk neuroblastoma; 3951=Phase I pilot study of multiple cycles of high dose chemotherapy with peripheral blood stem cell infusions in advanced stage neuroblastoma.; 4941=National Wilms tumor study V - therapeutic trial & biology study; 8605=Study of the combination of ifosfamide, mesna, and VP-16 in children and young adults with recurrent sarcomas, PNET and other tumors; 8742=Phase III portion of 8741 for neuroblastoma; 9047=Neuroblastoma biology protocol; 9082=Protocol for the development of intervention strategies to reduce the time between symptom onset and diagnosis of childhood cancer -a pediatric oncology group cancer control study; 9140=Therapy for patients with recurrent or refractory neuroblastoma - a phase II study; 9262=A Phase II study of taxol in children with recurrent/refractory soft-tissue sarcoma, rhabdomyosarcoma, osteosarcoma, Ewing's sarcoma, neuroblastoma, germ cell tumors, Wilms' tumor, hepatoblastoma, and hepatocellular carcinoma, a POG study; 9280=Neuroblastoma epidemiology protocol - A Non-Therapeutic Study - A Joint Project of: The University of North Carolina, The Pediatric Oncology Group and The Children's Cancer Study Group; 9340=Treatment of patients >365 days at diagnosis with stage IV NBL: Upfront Phase II Window - A Phase II Study; 9341=Treatment of patients >365 days at diagnosis with stage IV and stage IIB/III (N-myc) NBL - a phase III study; 9342=Neuroblastoma #5, bone marrow transplant - a phase III study; 9343=Interleukin-6 in children receiving autologous bone marrow transplantation for advanced neuroblastoma - a pediatric oncology group phase I trial; 9361=Topotecan in pediatric patients with recurrent or progressive solid tumors - a pediatric oncology group phase II study; 9375=Topotecan plus cyclophosphamide in children with solid tumors - a pediatric oncology group phase I trial; 9464=Cyclophosphamide plus topotecan in children with recurrent or refractory solid tumors - a pediatric oncology group phase II study; 9640=Treatment of patients with high risk neuroblastoma (a feasibility pilot) using two cycles of marrow ablative chemotherapy followed by rescue With peripheral blood stem cells (PBSC), radiation therapy; A3973=A randomized study of purged vs. unpurged PBSC transplant following dose intensive induction therapy for high risk NBL; AADM01P1=Protocol for registration and consent to the childhood cancer research network: a limited institution pilot; AAML00P2=A dose finding study of the safety of gemtuzumab ozogamicin combined with conventional chemotherapy for patients with relapsed or refractory acute myeloid leukemia; ACCL0331=A Randomized double blind placebo controlled clinical trial to assess the efficacy of traumeel® S (IND # 66649) for the prevention and treatment of mucositis in children undergoing hematopoietic stem cell transplantation; ACCRN07=Protocol for the enrollment on the official COG registry, The Childhood Cancer Research Network (CCRN); ADVL0018=Phase I study of hu14.18-IL2 fusion protein in patients with refractory neuroblastoma and other refractory GD2 expressing tumors; ADVL0212=A Phase I study of depsipeptide (NSC#630176, IND# 51810) in pediatric patients with refractory solid tumors and leukemias; ADVL0214=A phase I study of single agent OSI-774 (Tarceva) (NSC # 718781, IND #63383) followed by OSI-774 with temozolomide for patients with selected recurrent/refractory solid tumors, including brain tumors; ADVL0215=A phase I study of decitabine in combination with doxorubicin and cyclophosphamide in the treatment of relapsed or refractory solid tumors; ADVL0421=A phase II study of oxaliplatin in children with recurrent solid tumors; ADVL0524=Phase II trial of ixabepilone (BMS-247550), an epothilone B analog, in children and young adults with refractory solid tumors; ADVL0525=A phase II study of pemetrexed in children with recurrent malignancies; ADVL06B1=A pharmacokinetic-pharmacodynamic-pharmacogenetic study of actinomycin-D and vincristine in children with cancer; ADVL0714=A phase I study of VEGF trap (NSC# 724770, IND# 100137) in children with refractory solid tumors; ALTE03N1=Key adverse events after childhood cancer; ALTE05N1=Umbrella long-term follow-up protocol; ANBL0032=Phase III randomized study of chimeric antibody 14.18 (Ch14.18) in high risk neuroblastoma following myeloablative therapy and autologous stem cell rescue; ANBL00B1=Neuroblastoma biology studies; ANBL00P1=A pilot study of tandem high dose chemotherapy with stem cell rescue following induction therapy in children with high risk neuroblastoma; ANBL02P1=A pilot induction regimen incorporating dose-intensive topotecan and cyclophosphamide for treatment of newly diagnosed high risk neuroblastoma; ANBL0321=Phase II study of fenretinide in pediatric patients with resistant or recurrent neuroblastoma; ANBL0322=A phase II study of hu14.18-IL2 (BB-IND-9728) in children with recurrent or refractory neuroblastoma; ANBL0532=Phase III randomized trial of single vs. tandem myeloablative as consolidation therapy for high-risk neuroblastoma; ANBL0621=A phase II study of ABT-751, an orally bioavailable tubulin binding agent, in children with relapsed or refractory neuroblastoma; B003=Diagnostic & prognostic studies in NBL; B903=Childhood cancer genetics; B947=Protocol for collection of biology specimens for research studies; B954=Opsoclonus-myoclonus-ataxia syndrome, neuroblastoma and the presence of anti-neuronal antibodies; B973=Laboratory-clinical studies of neuroblastoma; E04=Self-administered epidemiology questionnaire; E18=A case-control study of risk factors for neuroblastoma; I03=Neuroblastoma, diagnostic/prognostic; N891=Parents' perceptions of randomization; P9462=Randomized treatment of recurrent neuroblastoma with topotecan regimens following desferrioxamine (POG only) in an investigational window; P9641=Primary surgical therapy for biologically defined low-risk neuroblastoma; P9761=A phase II trial of irinotecan in children with refractory solid tumors; P9963=A phase II trial of rebeccamycin analogue (NSC #655649) in children with solid tumors; R9702=Prognostic implications of MIBG uptake in patients with neuroblastoma previously treated on CCG-3891; S31=Right atrial catheter study; S921=Comparison of urokinase vs heparin in preventing Infection in central venous devices in children with malignancies]"""
#     chunks = ""
#     is_the_beginning = True
#     max_chars = 2000
#     padding_words = 3
#     counter = 0
#     print(len(text))
#     # divvy up into chunks,  sum of each chunk should equal the original text.
#     for chunk in annotator.sliding_window(text=text, max_characters=max_chars, padding_words= padding_words):
#         assert len(chunk) <= max_chars
#         counter += 1
#         if is_the_beginning:
#             chunks += chunk
#         else:
#             # remove redundand padded words from final result
#             chunks += " ".join(chunk.split(" ")[padding_words:])
#         is_the_beginning = False

#     print(counter)
#     # since spaces are trimmed by tokenizer , we can execuled all spaces and do char
#     assert chunks == text