from pathlib import Path
from typing import Callable, Iterator

Loader = Callable[[str], Iterator[Path]]
