import os
from unittest import mock

from helx.search.config import Config


@mock.patch.dict(os.environ, {
    "ELASTIC_PASSWORD": "ohwhoa",
    "REDIS_PASSWORD": "thatsprettyneat",
    "NBOOST_API_HOST": "gettinboosted!"
})
def test_config_created_from_env_vars():
    cfg = Config.from_env()

    assert cfg.elastic_password == "ohwhoa"
    assert cfg.redis_password == "thatsprettyneat"
    assert cfg.nboost_host == "gettinboosted!"
