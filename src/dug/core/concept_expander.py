import logging
import threading

import requests

import dug.core.tranql as tql

logger = logging.getLogger('dug')

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class ConceptExpander:
    """Expands an identifier into knowledge graphs via TranQL.

    Responses are cached by the http session rather than by writing json to
    a crawlspace directory. The session cache keys a POST on its body, and
    the body here is the generated TranQL query, so it is exactly as
    cacheable as the files were -- but it expires, it is shared by every
    process pointing at the same backend, and it costs no disk. The files
    never expired, so a stale knowledge graph was served indefinitely, and
    two crawls writing the same identifier concurrently could leave a
    truncated file that failed to parse.

    `session_factory` is called once per thread, because requests.Session is
    not documented as thread safe and expand_concept fetches concurrently.
    """

    def __init__(self, url, min_tranql_score=0.2, session_factory=None):
        self.url = url
        self.min_tranql_score = min_tranql_score
        self.include_node_keys = ["id", "name", "synonyms"]
        self.include_edge_keys = []
        self.tranql_headers = {"accept": "application/json", "Content-Type": "text/plain"}
        self._session_factory = session_factory or requests.Session
        self._local = threading.local()

    @property
    def session(self):
        session = getattr(self._local, 'session', None)
        if session is None:
            session = self._session_factory()
            self._local.session = session
        return session

    def is_acceptable_answer(self, answer):
        return True

    def expand_identifier(self, identifier, query_factory, kg_filename=None, include_all_attributes=False):

        answer_kgs = []

        query = query_factory.get_query(identifier)
        logger.debug(query)
        response = self.session.post(
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

        # Get nodes in knowledge graph hashed by ids for easy lookup
        noMessage = (len(response.get("message",{})) == 0)
        statusError = (response.get("status","") == 'Error')
        if noMessage or statusError:
            # Skip on error
            logger.info(f"Error with identifier: {identifier}, response: {response}")
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
    