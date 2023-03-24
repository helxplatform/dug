import json
import logging
import os
import uvicorn

from fastapi import FastAPI
from dug.config import Config
from dug.core.async_search import Search
from pydantic import BaseModel

logger = logging.getLogger (__name__)

APP = FastAPI(
    title="Dug Search API",
    root_path=os.environ.get("ROOT_PATH", "/"),
)


class GetFromIndex(BaseModel):
    index: str = "concepts_index"
    size: int = 0


class SearchQueryModel(BaseModel):
    index: str
    query: str
    offset: int = 0
    size: int = 20


search = Search(Config.from_env())


@APP.post('/dump_concepts')
async def dump_concepts(request: GetFromIndex):
    logger.debug(f"search:{json.dumps(request.json())}")
    logger.info(f"search: {json.dumps(request.json(), indent=2)}")
    return {
        "message": "Dump result",
        "result": await search.dump_concepts(**request.dict()),
        "status": "success"
    }


@APP.get('/agg_data_types')
async def agg_data_types():
    return {
        "message": "Dump result",
        "result": await search.agg_data_type(),
        "status": "success"
    }


@APP.post('/search')
async def search_concepts(search_query: SearchQueryModel):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "concepts_index"
        "results": await search.search_concepts(**search_query.dict(exclude="index")),
        "status": "success"
    }


@APP.post('/search_kg')
async def search_kg(search_query: SearchQueryModel):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "kg_index"
        "results": await search.search_kg(**search_query.dict(exclude="index")),
        "status": "success"
    }


@APP.post('/search_var')
async def search_var(search_query: SearchQueryModel):
    return {
        "message": "Search result",
        # Although index in provided by the query we will keep it around for backward compatibility, but
        # search concepts should always search against "variables_index"
        "results": await search.search_concepts(**search_query.dict(exclude="index")),
        "status": "success"
    }


if __name__ == '__main__':
    uvicorn.run(APP)