from pathlib import Path
from typing import Iterator

from dug_data_model.v2 import InputFile


def load_from_filesystem(filepath: InputFile) -> Iterator[Path]:

    filepath = Path(filepath)
    if not filepath.exists():
        raise ValueError(f"Unable to locate {filepath}")

    if filepath.is_file():
        yield filepath
    else:
        print(filepath.glob("**/*"))
        yield from filepath.glob("**/*")
