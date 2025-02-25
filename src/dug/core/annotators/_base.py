import json
import logging
import re
import logging
import urllib.parse
from typing import Union, Callable, Any, Iterable, TypeVar, Generic, List, Optional
from dug import utils as utils
from requests import Session
import bmt
from retrying import retry

logger = logging.getLogger("dug")

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class DugIdentifier:
    """Core information about a concept, produced from annotator request

    The Dug Identifier is the core piece of information about a concept that
    produced from a request to an annotator based on a some original source of
    data.

    \n The information that is being stored is mostly meant to support the
    Monarch API but should be adjusted accordingly to suit new Annotators needs
    in the future.
    \n The information that will be needed for all annotators are:
        \n id: The CURIE identifier
        \n label: The CURIE identifier
        \n description: The CURIE identifier
    \n When there is another supported Normalizer it will be seperated into a
    separate plugin like annotator.
    """

    def __init__(self, id, label, types=None, search_text="", description=""):
        "custom init stores parameters to initial values"

        self.id = id
        self.label = label
        self.description = description
        if types is None:
            types = []
        self.types = types
        self.search_text = sorted([search_text]) if search_text else []
        self.equivalent_identifiers = []
        self.synonyms = []
        self.purl = ""

    @property
    def id_type(self):
        return self.id.split(":")[0]

    def add_search_text(self, text):
        "Add text only if it's unique and if not empty string"
        if text and text not in self.search_text:
            self.search_text = sorted(self.search_text + [text])

    def get_searchable_dict(self):
        "Return version of identifier compatible with what's in ElasticSearch"
        es_ident = {
            "id": self.id,
            "label": self.label,
            "equivalent_identifiers": self.equivalent_identifiers,
            "type": self.types,
            "synonyms": self.synonyms,
        }
        return es_ident

    def jsonable(self):
        "Output pickleable object (used by utils.complex_handler)"
        return self.__dict__


    def __str__(self):
        return json.dumps(self.__dict__, indent=2, default=utils.complex_handler)


Input = TypeVar("Input")
Output = TypeVar("Output")


class AnnotatorSession(Generic[Input, Output]):
    def make_request(self, value: Input, http_session: Session):
        raise NotImplementedError()

    def handle_response(self, value, response: Union[dict, list]) -> Output:
        raise NotImplementedError()

    def __call__(self, value: Input, http_session: Session) -> Output:
        response = self.make_request(value, http_session)

        result = self.handle_response(value, response)

        return result


class DefaultNormalizer():
    """Default concept normalizer class

    After annotation there must be a Normalizing step to collasce equivalent
    concepts into one official concept. This is a needed step for the knowledge
    graph to map between different concepts.

    The reason why this class in integrated into the annotators.py is because
    currently there is only one supported Normalizer through the NCATs
    Translator API.

    When there is another supported Normalizer it will be seperated into a
    separate plugin like annotator.
    """

    def __init__(self, url):
        self.bl_toolkit = bmt.Toolkit()
        self.url = url

    def __call__(self, identifier: DugIdentifier, http_session: Session) -> DugIdentifier:
        # Use RENCI's normalization API service to get the preferred version of an identifier
        logger.debug(f"Normalizing: {identifier.id}")
        response = self.make_request(identifier, http_session)
        result = self.handle_response(identifier, response)
        return result

    def make_request(self, value: DugIdentifier, http_session: Session) -> dict:
        curie = value.id
        url = f"{self.url}{urllib.parse.quote(curie)}"
        try:
            response = http_session.get(url)
        except Exception as get_exc:
            logger.info(f"Error normalizing {value} at {url}")
            logger.error(f"Error {get_exc.__class__.__name__}: {get_exc}")
            return {}
        try:
            normalized = response.json()
        except Exception as json_exc:
            logger.info(
                f"Error processing response: {response.text} (HTTP {response.status_code})"
            )
            logger.error(f"Error {json_exc.__class__.__name__}: {json_exc}")
            return {}

        return normalized

    def handle_response(
        self, identifier: DugIdentifier, normalized: dict
    ) -> Optional[DugIdentifier]:
        """Record normalized results."""
        curie = identifier.id
        normalization = normalized.get(curie, {})
        if normalization is None:
            logger.info(
                f"Normalization service did not return normalization for: {curie}"
            )
            return None

        preferred_id = normalization.get("id", {})
        equivalent_identifiers = normalization.get("equivalent_identifiers", [])
        biolink_type = normalization.get("type", [])

        # Return none if there isn't actually a preferred id
        if "identifier" not in preferred_id:
            logger.debug(f"ERROR: normalize({curie})=>({preferred_id}). No identifier?")
            return None

        logger.debug(f"Preferred id: {preferred_id}")
        identifier.id = preferred_id.get("identifier", "")
        identifier.label = preferred_id.get("label", "")
        identifier.description = preferred_id.get("description", "")
        identifier.equivalent_identifiers = [
            v["identifier"] for v in equivalent_identifiers
        ]
        try:
            identifier.types = self.bl_toolkit.get_element(biolink_type[0]).name
        except:
            # converts biolink:SmallMolecule to small molecule
            identifier.types = (
                " ".join(
                    re.split("(?=[A-Z])", biolink_type[0].replace("biolink:", ""))[1:]
                )
            ).lower()
        return identifier


class DefaultSynonymFinder():
    """ The SynonymFinder stores synonyms for concepts in the knowledge graph so users in the Dug User Interface can find concepts that match their search criteria. 
    \n The reason why this class in integrated into the annotators.py is because currently there is only one supported SynonymFinder through the deployed by RENCI.
    \n When there is another supported SynonymFinder it will be seperated into a separate plugin like annotator.
    """

    def __init__(self, url: str):
        self.url = url

    # def get_identifier_synonyms
    def __call__(self, curie: str, http_session):
        """
        This function uses the NCATS translator service to return a list of synonyms for
        curie id
        """
        response = self.make_request(curie, http_session)
        result = self.handle_response(curie, response)
        return result

    @retry(stop_max_attempt_number=3)
    def make_request(self, curie: str, http_session: Session):
        # Get response from namelookup reverse lookup op
        # example (https://name-resolution-sri.renci.org/docs#/lookup/lookup_names_reverse_lookup_post)
        url = f"{self.url}"
        payload = {"curies": [curie]}
        try:
            response = http_session.post(url, json=payload)
            if str(response.status_code).startswith("4"):
                logger.error(
                    f"No synonyms returned for: `{curie}`. Validation error: {response.text}"
                )
                return {curie: {"names": []}}
            if str(response.status_code).startswith("5"):
                logger.error(
                    f"No synonyms returned for: `{curie}`. Internal server error from {self.url}. Error: {response.text}"
                )
                return {curie: {"names": []}}
            return response.json()
        except json.decoder.JSONDecodeError as e:
            logger.error(
                f"Json parse error for response from `{url}`. Exception: {str(e)}"
            )
            return {curie: {"names": []}}

    def handle_response(self, curie: str, raw_synonyms: List[dict]) -> List[str]:
        # Return curie synonyms
        return raw_synonyms.get(curie, {}).get('names', [])


Indexable = Union[DugIdentifier, AnnotatorSession]
# Indexable = DugIdentifier
Annotator = Callable[[Any], Iterable[Indexable]]
# Annotator = Callable[[Any], Iterable[DugIdentifier]]
