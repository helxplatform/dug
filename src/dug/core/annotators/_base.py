import json
import logging
from typing import Union, Callable, Any, Iterable, Awaitable, TypeVar, Generic
from dug import utils as utils
from requests import Session
from dug.config import Config as AnnotatorConfig

logger = logging.getLogger('dug')

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


class DugIdentifier:
    def __init__(self, id, label, types=None, search_text="", description=""):
        self.id = id
        self.label = label
        self.description = description
        if types is None:
            types = []
        self.types = types
        self.search_text = [search_text] if search_text else []
        self.equivalent_identifiers = []
        self.synonyms = []
        self.purl = ""

    def jsonable(self):
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

# def build_annotator(self) -> DugAnnotator:

#     preprocessor = Preprocessor(**self.config.preprocessor)
#     annotator = Annotate(**self.config.annotator)
#     normalizer = Normalizer(**self.config.normalizer)
#     synonym_finder = SynonymFinder(**self.config.synonym_service)

#     annotator = DugAnnotator(
#         preprocessor=preprocessor,
#         annotator=annotator,
#         normalizer=normalizer,
#         synonym_finder=synonym_finder
#     )

#     return annotator

Indexable = Union[DugIdentifier, AnnotatorSession]
# Indexable = DugIdentifier
Annotator = Callable[[Any], Iterable[Indexable]]
# Annotator = Callable[[Any], Iterable[DugIdentifier]]