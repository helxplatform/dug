import json
import logging
import os
import re
import urllib.parse
from typing import TypeVar, Generic, Union, List, Tuple, Optional
import bmt
import requests
from requests import Session

from ._base import DugIdentifier, AnnotatorSession, Input, AnnotatorConfig
from dug.core.annotators.utils.biolink_purl_util import BioLinkPURLerizer

logger = logging.getLogger('dug')

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class AnnotateMonarch:
    def __init__(
            self,
            config: AnnotatorConfig,
            preprocessor: "PreprocessorMonarch",
            annotator: "AnnotatorMonarch",
            normalizer: "NormalizerMonarch",
            synonym_finder: "SynonymFinderMonarch",
            ontology_greenlist=[],
    ):
        self.config = config
        self.preprocessor = preprocessor(**self.config.preprocessor)
        self.annotator = annotator(**self.config.annotator)
        self.normalizer = normalizer(**self.config.normalizer)
        self.synonym_finder = synonym_finder(**self.config.synonym_service)
        self.ontology_greenlist = ontology_greenlist
        self.norm_fails_file = "norm_fails.txt"
        self.anno_fails_file = "anno_fails.txt"

    def annotate(self, text, http_session):

        # Preprocess text (debraviate, remove stopwords, etc.)
        text = self.preprocessor.preprocess(text)

        # Fetch identifiers
        raw_identifiers = self.annotator.annotate(text, http_session)

        # Write out to file if text fails to annotate
        if not raw_identifiers:
            with open(self.anno_fails_file, "a") as fh:
                fh.write(f'{text}\n')

        processed_identifiers = []
        for identifier in raw_identifiers:

            # Normalize identifier using normalization service
            norm_id = self.normalizer.normalize(identifier, http_session)

            # Skip adding id if it doesn't normalize
            if norm_id is None:
                # Write out to file if identifier doesn't normalize
                with open(self.norm_fails_file, "a") as fh:
                    fh.write(f'{identifier.id}\n')

                # Discard non-normalized ident if not in greenlist
                if identifier.id_type not in self.ontology_greenlist:
                    continue

                # If it is in greenlist just keep moving forward
                norm_id = identifier

            # Add synonyms to identifier
            norm_id.synonyms = self.synonym_finder.get_synonyms(norm_id.id, http_session)

            # Get pURL for ontology identifer for more info
            norm_id.purl = BioLinkPURLerizer.get_curie_purl(norm_id.id)
            processed_identifiers.append(norm_id)

        return processed_identifiers

class PreprocessorMonarch:
    """"Class for preprocessing strings so they are better interpreted by NLP steps"""

    def __init__(self, debreviator=None, stopwords=None):
        if debreviator is None:
            debreviator = self.default_debreviator_factory()
        self.decoder = debreviator

        if stopwords is None:
            stopwords = []
        self.stopwords = stopwords

    def preprocess(self, text: str) -> str:
        """
        Apply debreviator to replace abbreviations and other characters

        >>> pp = PreprocessorMonarch({"foo": "bar"}, ["baz"])
        >>> pp.preprocess("Hello foo")
        'Hello bar'

        >>> pp.preprocess("Hello baz world")
        'Hello world'
        """

        for key, value in self.decoder.items():
            text = text.replace(key, value)

        # Remove any stopwords
        text = " ".join([word for word in text.split() if word not in self.stopwords])
        return text

    @staticmethod
    def default_debreviator_factory():
        return {"bmi": "body mass index", "_": " "}


# Input = TypeVar("Input")
# Output = TypeVar("Output")


# class ApiClient(Generic[Input, Output]):

#     def make_request(self, value: Input, http_session: Session):
#         raise NotImplementedError()

#     def handle_response(self, value, response: Union[dict, list]) -> Output:
#         raise NotImplementedError()

#     def __call__(self, value: Input, http_session: Session) -> Output:
#         response = self.make_request(value, http_session)

#         result = self.handle_response(value, response)

#         return result


class AnnotatorMonarch(AnnotatorSession[str, List[DugIdentifier]]):
    """
    Use monarch API service to fetch ontology IDs found in text
    """

    def __init__(self, url: str):
        self.url = url

    def sliding_window(self, text, max_characters=2000, padding_words=5):
        """
        For long texts sliding window works as the following
        "aaaa bbb ccc ddd eeee"
        with a sliding max chars 8 and padding 1
        first yeild would be "aaaa bbb"
        next subsequent yeilds "bbb ccc", "ccc ddd" , "ddd eeee"
        allowing context to be preserved with the scope of padding
        For a text of length 7653 , with max_characters 2000 and padding 5 , 4 chunks are yielded.
        """
        words = text.split(' ')
        total_words = len(words)
        window_end = False
        current_index = 0
        while not window_end:
            current_string = ""
            for index, word in enumerate(words[current_index: ]):
                if len(current_string) + len(word) + 1 >= max_characters:
                    yield current_string + " "
                    current_index += index - padding_words
                    break
                appendee = word if index == 0 else " " + word
                current_string += appendee

            if current_index + index == len(words) - 1:
                window_end = True
                yield current_string

    def annotate(self, text, http_session):
        logger.debug(f"Annotating: {text}")
        identifiers = []
        for chunk_text in self.sliding_window(text):
            identifiers += self(chunk_text, http_session)
        return identifiers

    def make_request(self, value: Input, http_session: Session):
        value = urllib.parse.quote(value)
        url = f'{self.url}{value}'

        # This could be moved to a config file
        NUM_TRIES = 5
        for _ in range(NUM_TRIES):
           response = http_session.get(url)
           if response is not None:
              # looks like it worked
              break

        # if the reponse is still None here, throw an error         
        if response is None:
            raise RuntimeError(f"no response from {url}")
        return response.json()

    def handle_response(self, value, response: dict) -> List[DugIdentifier]:
        identifiers = []
        """ Parse each identifier and initialize identifier object """
        for span in response.get('spans', []):
            search_text = span.get('text', None)
            for token in span.get('token', []):
                curie = token.get('id', None)
                if not curie:
                    continue

                biolink_types = token.get('category')
                label = token.get('terms')[0]
                identifiers.append(DugIdentifier(id=curie,
                                              label=label,
                                              types=biolink_types,
                                              search_text=search_text))
        return identifiers


class NormalizerMonarch(AnnotatorSession[DugIdentifier, DugIdentifier]):
    def __init__(self, url):
        self.bl_toolkit = bmt.Toolkit()
        self.url = url

    def normalize(self, identifier: DugIdentifier, http_session: Session):
        # Use RENCI's normalization API service to get the preferred version of an identifier
        logger.debug(f"Normalizing: {identifier.id}")
        return self(identifier, http_session)

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
            logger.info(f"Error processing response: {response.text} (HTTP {response.status_code})")
            logger.error(f"Error {json_exc.__class__.__name__}: {json_exc}")
            return {}

        return normalized

    def handle_response(self, identifier: DugIdentifier, normalized: dict) -> Optional[DugIdentifier]:
        """ Record normalized results. """
        curie = identifier.id
        normalization = normalized.get(curie, {})
        if normalization is None:
            logger.info(f"Normalization service did not return normalization for: {curie}")
            return None

        preferred_id = normalization.get("id", {})
        equivalent_identifiers = normalization.get("equivalent_identifiers", [])
        biolink_type = normalization.get("type", [])

        # Return none if there isn't actually a preferred id
        if 'identifier' not in preferred_id:
            logger.debug(f"ERROR: normalize({curie})=>({preferred_id}). No identifier?")
            return None

        logger.debug(f"Preferred id: {preferred_id}")
        identifier.id = preferred_id.get('identifier', '')
        identifier.label = preferred_id.get('label', '')
        identifier.description = preferred_id.get('description', '')
        identifier.equivalent_identifiers = [v['identifier'] for v in equivalent_identifiers]        
        try: 
            identifier.types = self.bl_toolkit.get_element(biolink_type[0]).name
        except:
            # converts biolink:SmallMolecule to small molecule 
            identifier.types = (" ".join(re.split("(?=[A-Z])", biolink_type[0].replace('biolink:', ''))[1:])).lower()
        return identifier


class SynonymFinderMonarch(AnnotatorSession[str, List[str]]):

    def __init__(self, url: str):
        self.url = url

    def get_synonyms(self, curie: str, http_session):
        '''
        This function uses the NCATS translator service to return a list of synonyms for
        curie id
        '''

        return self(curie, http_session)

    def make_request(self, curie: str, http_session: Session):
        # Get response from namelookup reverse lookup op
        # example (https://name-resolution-sri.renci.org/docs#/lookup/lookup_names_reverse_lookup_post)
        url = f"{self.url}"
        payload = {
            'curies': [curie]
        }
        try:
            response = http_session.post(url, json=payload)
            if str(response.status_code).startswith('4'):
                logger.error(f"No synonyms returned for: `{curie}`. Validation error: {response.text}")
                return {curie: []}
            if str(response.status_code).startswith('5'):
                logger.error(f"No synonyms returned for: `{curie}`. Internal server error from {self.url}. Error: {response.text}")
                return {curie: []}
            return response.json()
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Json parse error for response from `{url}`. Exception: {str(e)}")
            return {curie: []}

    def handle_response(self, curie: str, raw_synonyms: List[dict]) -> List[str]:
        # Return curie synonyms
        return raw_synonyms.get(curie, [])