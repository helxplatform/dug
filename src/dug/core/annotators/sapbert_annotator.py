import logging
from typing import List
from requests import Session
import json

from dug.core.annotators._base import DugIdentifier, Input
from dug.core.annotators.utils.biolink_purl_util import BioLinkPURLerizer

logger = logging.getLogger("dug")

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class AnnotateSapbert:
    """
    Use the RENCI Sapbert API service to fetch ontology IDs found in text
    """

    def __init__(
        self,
        normalizer,
        synonym_finder,
        ontology_greenlist=[],
        **kwargs
    ):
        self.classificationUrl = kwargs.get('classification_url')
        self.annotatorUrl = kwargs.get('annotator_url')

        if not self.classificationUrl:
            raise TypeError('Classification url needs to be defined for sapbert annotator')
        if not self.annotatorUrl:
            raise TypeError('Annotator url needs to be defined for sapbert annotator')
        self.normalizer = normalizer
        self.synonym_finder = synonym_finder
        self.ontology_greenlist = ontology_greenlist
        self.norm_fails_file = "norm_fails.txt"
        self.anno_fails_file = "anno_fails.txt"
        # threshold marking cutoff point
        self.score_threshold = kwargs.get("score_threshold", 0.8)
        # indicate if we want values above or below the threshold.
        self.score_direction_up = True if kwargs.get("score_direction", "up") == "up" else False

    def __call__(self, text, http_session) -> List[DugIdentifier]:
        # Fetch identifiers
        classifiers: List = self.text_classification(text, http_session)

        raw_identifiers: List[DugIdentifier] = self.annotate_classifiers(
            classifiers, http_session
        )

        # Write out to file if text fails to annotate
        if not raw_identifiers:
            with open(self.anno_fails_file, "a") as fh:
                fh.write(f"{text}\n")

        processed_identifiers = []
        for identifier in raw_identifiers:
            # Normalize identifier using normalization service
            norm_id = self.normalizer(identifier, http_session)

            # Skip adding id if it doesn't normalize
            if norm_id is None:
                # Write out to file if identifier doesn't normalize
                with open(self.norm_fails_file, "a") as fh:
                    fh.write(f"{identifier.id}\n")

                # Discard non-normalized ident if not in greenlist
                if identifier.id_type not in self.ontology_greenlist:
                    continue

                # If it is in greenlist just keep moving forward
                norm_id = identifier

            # Add synonyms to identifier
            norm_id.synonyms = self.synonym_finder(norm_id.id, http_session)

            # Get pURL for ontology identifer for more info
            norm_id.purl = BioLinkPURLerizer.get_curie_purl(norm_id.id)
            processed_identifiers.append(norm_id)

        return processed_identifiers

    def text_classification(self, text, http_session) -> List:
        """
        Send variable text to a token classifier API and return list of classified terms and biolink types

        Param:
          text: String -- Full variable text, API does text preprocessing

        Request:
          {
              "text": "{{text}}",
              "model_name": "token_classification"
          }

        Response: List of dicts from which we want to extract the following:
          {
              "obj": "{{Biolink Classification}}",
              "text": "{{Classified Term}}"
          }

        Returns: List Dicts each with a Classified Term and Biolink Classification
        """
        logger.debug(f"Classification")
        response = self.make_classification_request(text, http_session)
        classifiers = self.handle_classification_response(response)
        return classifiers

    def make_classification_request(self, text: Input, http_session: Session):
        url = self.classificationUrl
        logger.debug(f"response from {text}")
        payload = {
            "text": text,
            "model_name": "token_classification",
        }
        # This could be moved to a config file
        NUM_TRIES = 5
        for _ in range(NUM_TRIES):
            response = http_session.post(url, json=payload)
            if response is not None:
                # looks like it worked
                break
        # if the reponse is still None here, throw an error
        if response is None:
            raise RuntimeError(f"no response from {url}")
        if response.status_code == 403:
            raise RuntimeError(f"You are not authorized to use this API -- {url}")
        if response.status_code == 500:
            raise RuntimeError(f"Classification API is temporarily down -- vist docs here: {url.replace('annotate', 'docs')}")
        return response.json()

    def handle_classification_response(self, response: dict) -> List:
        classifiers = []
        """ Parse each identifier and initialize identifier object """
        for denotation in response.get("denotations", []):
            text = denotation.get("text", None)
            bl_type = denotation.get("obj", None)
            classifiers.append(
                {"text": text, "bl_type": bl_type}
            )
        return classifiers

    def annotate_classifiers(
        self, classifiers: List, http_session
    ) -> List[DugIdentifier]:
        """
        Send Classified Terms to Sapbert API

        Param:
          List: [
              term_dict: Dict {
                  "text": String -- Classified term received from token classification API
                  "bl_type": String -- Biolink Classification
              }
          ]

        Request:
          {
              "text": "{{term_dict['text']}}",
              "model_name": "sapbert",
              "count": {{Limits the number of results}},
              "args": {
                  "bl_type": "{{ term_dict['bl_type'] -- NOTE omit `biolink:`}}"
              }
          }

        Response: List of dicts with the following structure:
              {
                  "name": "{{Identified Name}}",
                  "curie": "{{Curie ID}}",
                  "category": "{{Biolink term with `biolink:`}}",
                  "score": "{{Float confidence in the annotation}}"
              }
          TBD: Organize the results by highest score
          Return: List of DugIdentifiers with a Curie ID
        """
        identifiers = []
        for term_dict in classifiers:
            logger.debug(f"Annotating: {term_dict['text']}")

            response = self.make_annotation_request(term_dict, http_session)
            identifiers += self.handle_annotation_response(term_dict, response)

        return identifiers

    def make_annotation_request(self, term_dict: Input, http_session: Session):
        url = self.annotatorUrl
        payload = {
            "text": term_dict["text"],
            "model_name": "sapbert",
            "count": 10,
            "args": {"bl_type": term_dict["bl_type"]},
        }
        # This could be moved to a config file
        NUM_TRIES = 5
        for _ in range(NUM_TRIES):
            response = http_session.post(url, json=payload)
            if response is not None:
                # looks like it worked
                break
        # if the reponse is still None here, throw an error
        if response is None:
            raise RuntimeError(f"no response from {url}")
        if response.status_code == 403:
            raise RuntimeError(f"You are not authorized to use this API -- {url}")
        if response.status_code == 500:
            raise RuntimeError(f"Annotation API is temporarily down -- vist docs here: {url.replace('annotate', 'docs')}")
        return response.json()

    def handle_annotation_response(self, value, response: dict) -> List[DugIdentifier]:
        identifiers = []
        """ Parse each identifier and initialize identifier object """
        for identifier in response:
            search_text = value.get("text", None)
            curie = identifier.get("curie", None)
            if not curie:
                continue

            biolink_type = identifier.get('category')
            score = identifier.get("score", 0)
            label = identifier.get("name")
            if score >= self.score_threshold and self.score_direction_up:
                identifiers.append(
                    DugIdentifier(id=curie, label=label, types=[biolink_type], search_text=search_text)
                )
            elif score <= self.score_threshold and not self.score_direction_up:
                identifiers.append(
                    DugIdentifier(id=curie, label=label, types=[biolink_type], search_text=search_text)
                )
        return identifiers

## Testing Purposes
# if __name__ == "__main__":
#     from dug.config import Config
#     import json
#     import redis
#     from requests_cache import CachedSession
#     from dug.core.annotators._base import DefaultNormalizer, DefaultSynonymFinder

#     config = Config.from_env()
#     annotator = AnnotateSapbert(
#         normalizer=DefaultNormalizer(**config.normalizer),
#         synonym_finder=DefaultSynonymFinder(**config.synonym_service),
#     )

#     redis_config = {
#         "host": "localhost",
#         "port": config.redis_port,
#         "password": config.redis_password,
#     }

#     http_sesh = CachedSession(
#         cache_name="annotator",
#         backend="redis",
#         connection=redis.StrictRedis(**redis_config),
#     )
#     annotator(text="Have you ever had a heart attack?", http_session=http_sesh)
