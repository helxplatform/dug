import json
import logging
import os
import traceback
from typing import List

from dug.core.parsers import Parser, DugElement, DugConcept
from dug.core.annotators import Annotator, DugIdentifier
import dug.core.tranql as tql
from dug.utils import biolink_snake_case, get_formatted_biolink_name

logger = logging.getLogger('dug')


class Crawler:
    def __init__(self, crawl_file: str, parser: Parser, annotator: Annotator,
                 tranqlizer, tranql_queries,
                 http_session, exclude_identifiers=None, element_type=None,
                 element_extraction=None):

        if exclude_identifiers is None:
            exclude_identifiers = []

        self.crawl_file = crawl_file
        self.parser: Parser = parser
        self.element_type = element_type
        self.annotator: Annotator = annotator
        self.tranqlizer = tranqlizer
        self.tranql_queries = tranql_queries
        self.http_session = http_session
        self.exclude_identifiers = exclude_identifiers
        self.element_extraction = element_extraction
        self.elements = []
        self.concepts = {}
        self.crawlspace = "crawl"

    def make_crawlspace(self):
        if not os.path.exists(self.crawlspace):
            try:
                os.makedirs(self.crawlspace)
            except Exception as e:
                print(f"-----------> {e}")
                traceback.print_exc()

    def crawl(self):

        # Create directory for storing temporary results
        self.make_crawlspace()

        # Read in elements from parser
        self.elements = self.parser(self.crawl_file)

        # Optionally coerce all elements to be a specific type
        for element in self.elements:
            if isinstance(element, DugElement) and self.element_type is not None:
                element.type = self.element_type

        # Annotate elements
        self.annotate_elements()

        # if elements are extracted from the graph this array will contain the new dug elements
        dug_elements_from_graph = []

        # Expand concepts to other concepts
        concept_file = open(f"{self.crawlspace}/concept_file.json", "w")
        for concept_id, concept in self.concepts.items():
            # Use TranQL queries to fetch knowledge graphs containing related but not synonymous biological terms
            self.expand_concept(concept)

            # Traverse identifiers to create single list of of search targets/synonyms for concept
            concept.set_search_terms()

            # Traverse kg answers to create list of optional search targets containing related concepts
            concept.set_optional_terms()

            # Remove duplicate search terms and optional search terms
            concept.clean()

            # Write concept out to a file
            concept_file.write(f"{json.dumps(concept.get_searchable_dict(), indent=2)}")

            if self.element_extraction:
                for element_extraction_config in self.element_extraction:
                    casting_config = element_extraction_config['casting_config']
                    tranql_source = element_extraction_config['tranql_source']
                    dug_element_type = element_extraction_config['output_dug_type']
                    dug_elements_from_graph += self.expand_to_dug_element(
                        concept=concept,
                        casting_config=casting_config,
                        dug_element_type=dug_element_type,
                        tranql_source=tranql_source
                    )

        # add new elements to parsed elements
        self.elements += dug_elements_from_graph

        # Set element optional terms now that concepts have been expanded
        # Open variable file for writing
        variable_file = open(f"{self.crawlspace}/element_file.json", "w")
        for element in self.elements:
            if isinstance(element, DugElement):
                element.set_optional_terms()
                variable_file.write(f"{element.get_searchable_dict()}\n")

        # Close concept, element files
        concept_file.close()
        variable_file.close()

    def annotate_elements(self):

        # Annotate elements/concepts and create new concepts based on the ontology identifiers returned
        logger.info(f"annotate {len(self.elements)} elements")
        for n, element in enumerate(self.elements):
            # If element is actually a pre-loaded concept (e.g. TOPMed Tag), add that to list of concepts
            if isinstance(element, DugConcept):
                self.concepts[element.id] = element

            # Annotate element with normalized ontology identifiers
            logger.info(f"annotate element #{n+1}/{len(self.elements)} '{element.id}'")
            self.annotate_element(element)
            if isinstance(element, DugElement):
                element.set_search_terms()

        # Now that we have our concepts and elements fully annotated, we need to
        # Make sure elements inherit the identifiers from their user-defined parent concepts
        # E.g. TOPMedTag1 was annotated with HP:123 and MONDO:12.
        # Each element assigned to TOPMedTag1 needs to be associated with those concepts as well
        for element in self.elements:
            # Skip user-defined concepts
            if isinstance(element, DugConcept):
                continue

            # Associate identifiers from user-defined concepts (see example above)
            # with child elements of those concepts
            concepts_to_add = []
            for concept_id, concept in element.concepts.items():
                for ident_id, identifier in concept.identifiers.items():
                    if ident_id not in element.concepts and ident_id in self.concepts:
                        concepts_to_add.append(self.concepts[ident_id])

            for concept_to_add in concepts_to_add:
                element.add_concept(concept_to_add)

    def annotate_element(self, element):

        # Annotate with a set of normalized ontology identifiers
        # self.DugAnnotator.annotator()
        identifiers: List[DugIdentifier] = self.annotator(text=element.ml_ready_desc,
                                              http_session=self.http_session)
        # Future thoughts... should we be passing in the stpe DugIdentifier here instead?


        # Each identifier then becomes a concept that links elements together
        for identifier in identifiers:
            if identifier.id not in self.concepts:
                # Create concept for newly seen identifier
                concept = DugConcept(concept_id=identifier.id,
                                                       name=identifier.label,
                                                       desc=identifier.description,
                                                       concept_type=identifier.types)
                # Add to list of concepts
                self.concepts[identifier.id] = concept

            # Add identifier to list of identifiers associated with concept
            self.concepts[identifier.id].add_identifier(identifier)

            # Create association between newly created concept and element
            # (unless element is actually a user-defined concept)
            if isinstance(element, DugElement):
                element.add_concept(self.concepts[identifier.id])

            # If element is actually a user defined concept (e.g. TOPMedTag), associate ident with concept
            # Child elements of these user-defined concepts will inherit all these identifiers as well.
            elif isinstance(element, DugConcept):
                element.add_identifier(identifier)

    def expand_concept(self, concept):

        # Get knowledge graphs of terms related to each identifier
        for ident_id, identifier in concept.identifiers.items():

            # Conditionally skip some identifiers if they are listed in config
            if ident_id in self.exclude_identifiers:
                continue

            # Use pre-defined queries to search for related knowledge graphs that include the identifier
            for query_name, query_factory in self.tranql_queries.items():

                # Skip query if the identifier is not a valid query for the query class
                if not query_factory.is_valid_curie(ident_id):
                    logger.info(f"identifier {ident_id} is not valid for query type {query_name}. Skipping!")
                    continue

                # Fetch kg and answer
                kg_outfile = f"{self.crawlspace}/{ident_id}_{query_name}.json"
                answers = self.tranqlizer.expand_identifier(ident_id, query_factory, kg_outfile)

                # Add any answer knowledge graphs to
                for answer in answers:
                    concept.add_kg_answer(answer, query_name=query_name)

    def expand_to_dug_element(self,
                              concept,
                              casting_config,
                              dug_element_type,
                              tranql_source):
        """
        Given a concept look up the knowledge graph to construct dug elements out of kg results
        does concept -> target_node_type crawls and converts target_node_type to dug element of type `dug_element_type`
        """
        elements = []
        # using node_type as the primary criteria for matching nodes to element type.
        target_node_type = casting_config["node_type"]
        curie_filter = casting_config["curie_prefix"]
        attribute_mapping = casting_config["attribute_mapping"]
        array_to_string = casting_config["list_field_choose_first"]
        # converts any of the following notations 
        # biolink:Publication , biolink.Publication  to publication 
        target_node_type_snake_case = biolink_snake_case(target_node_type.replace("biolink.", "").replace("biolink:", ""))
        for ident_id, identifier in concept.identifiers.items():

            # Check to see if the concept identifier has types defined, this is used to create
            # tranql queries below.
            if not identifier.types:
                continue

            # convert the first type to snake case to be used in tranql query.
            # first type is the leaf type, this is coming from Node normalization.
            # note when using bmt it returns biolink: prefix so we need to replace biolink: and snake case it for tranql.
            node_type = biolink_snake_case(get_formatted_biolink_name(identifier.types).replace("biolink:", ""))
            try:
                # Tranql query factory currently supports select node types as valid query
                # Types missing from QueryFactory.data_types will be skipped with this try catch
                query = tql.QueryFactory([node_type, target_node_type_snake_case], tranql_source)
            except tql.InvalidQueryError as exception:
                logger.debug(f"Skipping  {ident_id}, {exception}")
                continue

            # check if tranql query object can use the curie.
            if query.is_valid_curie(ident_id):
                logger.info(f"Expanding {ident_id} to other dug elements")
                # Fetch kg and answer
                # Fetch kg and answer
                # replace ":" with "~" to avoid windows os errors
                kg_outfile = f"{self.crawlspace}/" + f"{ident_id}_{target_node_type}.json".replace(":", "~")

                # query tranql, answers will include all node and edge attributes
                answers = self.tranqlizer.expand_identifier(ident_id, query,
                                                            kg_filename=kg_outfile,
                                                            include_all_attributes=True)
                # for each answer construct a dug element
                for answer in answers:
                    # here we will inspect the answers create new dug elements based on target node type
                    # and return the variables.
                    for node_id, node in answer.nodes.items():
                        # support both biolink. and biolink: prefixes
                        snake_case_category = [
                            biolink_snake_case(cat.replace("biolink.", "").replace("biolink:", "")) 
                            for cat in node['category']
                            ]
                        if target_node_type_snake_case in snake_case_category:
                            if node['id'].startswith(curie_filter):
                                element_attribute_args = {"elem_id": node_id, "elem_type": dug_element_type}
                                for key in attribute_mapping:
                                    mapped_value = node.get(attribute_mapping[key], "")
                                    # treat all attributes as strings 
                                    if key in array_to_string and isinstance(mapped_value, list) and len(mapped_value) > 0:
                                        mapped_value = mapped_value[0]
                                    element_attribute_args.update({key: mapped_value})
                                element = DugElement(
                                    **element_attribute_args
                                )
                                element.add_concept(concept)
                                elements.append(element)
        return elements
