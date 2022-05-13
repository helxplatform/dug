import urllib
import logging
from typing import List

from requests import Session

from dug.core.annotate import ApiClient, Identifier, Input

logger = logging.getLogger('dug')


class Annotator(ApiClient[str, List[Identifier]]):
    """
    Use monarch API service to fetch ontology IDs found in text
    """

    def __init__(self, url: str):
        self.url = url

    def annotate(self, text, http_session):
        logger.debug(f"Annotating: {text}")
        return self(text, http_session)

    def make_request(self, value: Input, http_session: Session):
        value = urllib.parse.quote(value)
        url = f'{self.url}{value}'
        response = http_session.get(url)
        if response is None:
            raise RuntimeError(f"no response from {url}")
        return response.json()

    def handle_response(self, value, response: dict) -> List[Identifier]:
        raise NotImplementedError("Class has not implemented handle_response method")