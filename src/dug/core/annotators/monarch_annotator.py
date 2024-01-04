import logging
import urllib.parse
from typing import List
from requests import Session

from dug.core.annotators._base import DugIdentifier, Input
from dug.core.annotators.utils.biolink_purl_util import BioLinkPURLerizer

logger = logging.getLogger('dug')

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class AnnotateMonarch:
    """
    Use monarch API service to fetch ontology IDs found in text
    """
    def __init__(
            self,
            normalizer,
            synonym_finder,
            config,
            ontology_greenlist=[],
            **kwargs
    ):

        self.annotatorUrl = kwargs['url']
        self.normalizer = normalizer
        self.synonym_finder = synonym_finder
        self.ontology_greenlist = ontology_greenlist
        self.norm_fails_file = "norm_fails.txt"
        self.anno_fails_file = "anno_fails.txt"

        debreviator = config.preprocessor['debreviator'] if 'debreviator' in config.preprocessor else None
        stopwords = config.preprocessor['stopwords'] if 'stopwords' in  config.preprocessor else None

        if debreviator is None:
            debreviator = self.default_debreviator_factory()
        self.decoder = debreviator

        if stopwords is None:
            stopwords = []
        self.stopwords = stopwords

    def __call__(self, text, http_session) -> List[DugIdentifier]:
        # Preprocess text (debraviate, remove stopwords, etc.)
        text = self.preprocess_text(text)

        # Fetch identifiers
        raw_identifiers = self.annotate_text(text, http_session)

        # Write out to file if text fails to annotate
        if not raw_identifiers:
            with open(self.anno_fails_file, "a") as fh:
                fh.write(f'{text}\n')

        processed_identifiers = []
        for identifier in raw_identifiers:

            # Normalize identifier using normalization service
            norm_id = self.normalizer(identifier, http_session)

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
            norm_id.synonyms = self.synonym_finder(norm_id.id, http_session)

            # Get pURL for ontology identifer for more info
            norm_id.purl = BioLinkPURLerizer.get_curie_purl(norm_id.id)
            processed_identifiers.append(norm_id)

        return processed_identifiers
    
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

    def annotate_text(self, text, http_session) -> List[DugIdentifier]:
        logger.debug(f"Annotating: {text}")
        identifiers = []
        for chunk_text in self.sliding_window(text):
            response = self.make_request(chunk_text, http_session)
            identifiers += self.handle_response(chunk_text, response)
        return identifiers

    def make_request(self, value: Input, http_session: Session):
        value = urllib.parse.quote(value)
        url = f'{self.annotatorUrl}{value}'

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
    
    def preprocess_text(self, text: str) -> str:
        """
        Apply debreviator to replace abbreviations and other characters

        # >>> pp = PreprocessorMonarch({"foo": "bar"}, ["baz"])
        # >>> pp.preprocess("Hello foo")
        # 'Hello bar'

        # >>> pp.preprocess("Hello baz world")
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