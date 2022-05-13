from typing import List

from .AnnotatorBase import Annotator
from ..annotate import Identifier


class MonarchNLPAnnotator(Annotator):

    def handle_response(self, value, response: dict) -> List[Identifier]:
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
                identifiers.append(Identifier(id=curie,
                                              label=label,
                                              types=biolink_types,
                                              search_text=search_text))
        return identifiers
