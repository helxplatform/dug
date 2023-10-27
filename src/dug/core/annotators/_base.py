import json
import logging
from typing import Union, Callable, Any, Iterable, Awaitable, TypeVar, Generic
from dug import utils as utils
from requests import Session

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

    @property
    def id_type(self):
        return self.id.split(":")[0]

    def add_search_text(self, text):
        # Add text only if it's unique and if not empty string
        if text and text not in self.search_text:
            self.search_text.append(text)

    def get_searchable_dict(self):
        # Return a version of the identifier compatible with what's in ElasticSearch
        es_ident = {
            'id': self.id,
            'label': self.label,
            'equivalent_identifiers': self.equivalent_identifiers,
            'type': self.types,
            'synonyms': self.synonyms
        }
        return es_ident

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

Indexable = Union[DugIdentifier, AnnotatorSession]
# Indexable = DugIdentifier
Annotator = Callable[[Any], Iterable[Indexable]]
# Annotator = Callable[[Any], Iterable[DugIdentifier]]