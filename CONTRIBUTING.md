# Development Guide 

## Setting up

To install from source code:

```shell
git clone git@github.com:helxplatform/dug.git && cd dug
pip install -r requirements.txt

bin/dug init

# Forthcoming: 
# pip install -e .
```

## Env Vars

Running `bin/dug dev init` will set up a .env file with the necessary environment variables that Dug needs
## Testing

Tests are developed using [pytest]().

The test suite includes doctests, unit tests in `tests/unit`, and integration tests in `tests/integration`.
The doctests and unit tests will always be runnable, but many of the integration tests expect some backend service (e.g. elasticsearch) to be running.

The entire test suite can be run with `python -m pytest` or, to only run unit tests, `python -m pytest tests/unit`

## Running

Dug has basically two functions: indexing and searching

### Backend

Dug relies on several backend services:
* ElasticSearch: [https://www.elastic.co/elasticsearch/](https://www.elastic.co/elasticsearch/)
* Redis
* Neo4J
* NBoost

You can run these however you like, as long as Dug can reach them,
but a docker-compose file is provided for your convenience:

```shell
docker-compose --env-file ./my.env -f docker/docker-compose.yaml up elasticsearch nboost neo4j redis
```

### Indexing

```shell
python -m dug.core --crawl-by-concept --crawl-file data/topmed_variables_v1.0.csv
bin/dug crawl_by_concept --crawl-file data/topmed_variables_v1.0.csv
```

### Searching

### API Server

Now that you have crawled some data, 

```shell
python3 -m dug.api
```

## Contributing

## Code quality

Dug does not currently implement any requirement for a specific code style. 
That policy may change. 

## VC Strategy

Dug devs prefer to use [gitflow](https://nvie.com/posts/a-successful-git-branching-model/). 
The TL;DR is:

    1. Work should never be committed directly to master or develop
    2. New work should be on a separate branch off of develop
        a. except hotfixes, which branch off master
    3. The develop branch should always be into a ready-to-release state
        a. no broken develop builds

## Writing good commit messages
