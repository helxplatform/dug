from .AnnotatorBase import Annotator
from ..annotate import Identifier
from typing import List


class ScigraphAnnotator(Annotator):
    def __init__(self, url):
        super(ScigraphAnnotator, self).__init__(url=url)

    def handle_response(self, value, response: dict) -> List[Identifier]:
        identifiers = []
        """ Parse each identifier and initialize identifier object """
        for span in response:
            token = span.get('token', {})
            curie = token.get('id')
            if not curie:
                continue
            label = token.get('terms')[0]
            biolink_types = token.get('category')
            identifiers.append(Identifier(id=curie,
                                          label=label,
                                          types=biolink_types,
                                          search_text=""))
        return identifiers
