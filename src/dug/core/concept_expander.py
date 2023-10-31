import json
import logging
import os
import requests

import dug.core.tranql as tql

logger = logging.getLogger('dug')

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class ConceptExpander:
    def __init__(self, url, min_tranql_score=0.2):
        self.url = url
        self.min_tranql_score = min_tranql_score
        self.include_node_keys = ["id", "name", "synonyms"]
        self.include_edge_keys = []
        self.tranql_headers = {"accept": "application/json", "Content-Type": "text/plain"}

    def is_acceptable_answer(self, answer):
        return True

    def expand_identifier(self, identifier, query_factory, kg_filename, include_all_attributes=False):

        answer_kgs = []

        # Skip TranQL query if a file exists in the crawlspace exists already, but continue w/ answers
        if os.path.exists(kg_filename):
            logger.info(f"identifier {identifier} is already crawled. Skipping TranQL query.")
            with open(kg_filename, 'r') as stream:
                response = json.load(stream)
        else:
            query = query_factory.get_query(identifier)
            logger.debug(query)
            response = requests.post(
                url=self.url,
                headers=self.tranql_headers,
                data=query).json()

            # Case: Skip if empty KG
            try:
                if response["message"] == 'Internal Server Error' or len(response["message"]["knowledge_graph"]["nodes"]) == 0:
                    logger.debug(f"Did not find a knowledge graph for {query}")
                    logger.debug(f"{self.url} returned response: {response}")
                    return []
            except KeyError as e:
                logger.error(f"Could not find key: {e} in response: {response}")

            # Dump out to file if there's a knowledge graph
            with open(kg_filename, 'w') as stream:
                json.dump(response, stream, indent=2)

        # Get nodes in knowledge graph hashed by ids for easy lookup
        noMessage = (len(response.get("message",{})) == 0)
        statusError = (response.get("status","") == 'Error')
        if noMessage or statusError:
            # Skip on error
            logger.info(f"Error with identifier: {identifier}, response: {response}, kg_filename: '{kg_filename}'")
            return []
        kg = tql.QueryKG(response)

        for answer in kg.answers:
            # Filter out answers that don't meet some criteria
            # Right now just don't filter anything
            logger.debug(f"Answer: {answer}")
            if not self.is_acceptable_answer(answer):
                logger.warning("Skipping answer as it failed one or more acceptance criteria. See log for details.")
                continue

            # Get subgraph containing only information for this answer
            try:
                # Temporarily surround in try/except because sometimes the answer graphs
                # contain invalid references to edges/nodes
                # This will be fixed in Robokop but for now just silently warn if answer is invalid
                node_attributes_filter = None if include_all_attributes else self.include_node_keys
                edge_attributes_filter = None if include_all_attributes else self.include_edge_keys
                answer_kg = kg.get_answer_subgraph(answer,
                                                   include_node_keys=node_attributes_filter,
                                                   include_edge_keys=edge_attributes_filter)

                # Add subgraph to list of acceptable answers to query
                answer_kgs.append(answer_kg)

            except tql.MissingNodeReferenceError:
                # TEMPORARY: Skip answers that have invalid node references
                # Need this to be fixed in Robokop
                logger.warning("Skipping answer due to presence of non-preferred id! "
                               "See err msg for details.")
                continue
            except tql.MissingEdgeReferenceError:
                # TEMPORARY: Skip answers that have invalid edge references
                # Need this to be fixed in Robokop
                logger.warning("Skipping answer due to presence of invalid edge reference! "
                               "See err msg for details.")
                continue

        return answer_kgs
    