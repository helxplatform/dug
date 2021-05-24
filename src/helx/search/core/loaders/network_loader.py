import logging
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import requests

from ._base import InputFile

logger = logging.getLogger('helx')


def load_from_network(data_storage_dir: InputFile, urls: str) -> Iterator[Path]:
    data_storage_dir = Path(data_storage_dir).resolve()
    url_list = urls.split(",")
    for url in url_list:
        logger.info(f"Fetching {url}")

        parse_result = urlparse(url)
        response = requests.get(url)

        if not response.ok:
            raise ValueError(f"Could not fetch {url}: {response.status_code}, {response.text}")

        nonroot_path = parse_result.path.lstrip('/')

        output_location = data_storage_dir / parse_result.netloc / nonroot_path
        output_location.parent.mkdir(parents=True, exist_ok=True)

        output_location.write_text(response.text)

        yield output_location