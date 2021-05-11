from pathlib import Path
from typing import Union, Iterable, Callable, Iterator

InputFile = Union[str, Path]

Loader = Callable[[str], Iterator[Path]]
