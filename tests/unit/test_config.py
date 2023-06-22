import os
from unittest import mock

from dug.config import Config


@mock.patch.dict(os.environ, {
    "ELASTIC_PASSWORD": "ohwhoa",
    "REDIS_PASSWORD": "thatsprettyneat"
})
def test_config_created_from_env_vars():
    cfg = Config.from_env()

    assert cfg.elastic_password == "ohwhoa"
    assert cfg.redis_password == "thatsprettyneat"
