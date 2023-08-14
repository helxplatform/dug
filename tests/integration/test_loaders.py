import tempfile
from pathlib import Path

import pytest

from dug.core.loaders.filesystem_loader import load_from_filesystem
from dug.core.loaders.network_loader import load_from_network
from tests.integration.conftest import TEST_DATA_DIR


def test_filesystem_loader():
    targets = load_from_filesystem(
        filepath=TEST_DATA_DIR / 'phs000166.v2.pht000700.v1.CAMP_CData.data_dict_2009_09_03.xml'
    )
    assert len(list(targets)) == 1

    targets = load_from_filesystem(
        filepath=TEST_DATA_DIR,
    )
    files = list(targets)
    assert len(files) == 15

    with pytest.raises(ValueError):
        targets = load_from_filesystem(
            filepath=TEST_DATA_DIR / "foo/bar"
        )
        next(targets)

    with pytest.raises(ValueError):
        targets = load_from_filesystem(
            filepath=TEST_DATA_DIR / "*.xml"
        )
        next(targets)


def test_network_loader():

    with tempfile.TemporaryDirectory(dir=TEST_DATA_DIR) as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        url = "https://github.com/helxplatform/dug/blob/develop/README.md"
        actual = next(load_from_network(tmp_dir, url))
        expected = tmp_dir_path / "github.com" / "helxplatform" / "dug" / "blob" / "develop" / "README.md"
        assert actual == expected
        assert actual.exists()

    with tempfile.TemporaryDirectory(dir=TEST_DATA_DIR) as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        with pytest.raises(ValueError):
            url = "https://github.com/helxplatform/dug/blob/develop/404 expected"
            next(load_from_network(tmp_dir, url))
        assert list(tmp_dir_path.iterdir()) == []
