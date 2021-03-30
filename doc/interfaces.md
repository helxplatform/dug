## Command Line Interface
```shell
# Display usage
dug -h

# Display installed version
dug --version

# Crawl 
dug crawl [target] [--parser] [--annotator] [--indexer] [--translator]

# Search
dug search [query]

dug show-config

#  indices:
#    -variable
#     -kg
```

## Python API

### Dug

The Dug class represents the main entry point to the system.
It has three main functions:

* Crawling: Take data from some source, and transform it into a knowledge graph,
* Indexing: Persist that knowledge graph in a data store
* Searching: Query the knowledge graph

```python

class Dug:
    
    def __init__(self, crawler, indexer, searcher):
        self.crawler = crawler
        self.indexer = indexer
        self.searcher = searcher
    
    def crawl(self, *args, **kwargs):
        """
        Making the calls to create a KG
        """
        ...
    
    def index(self, *args, **kwargs):
        """
        Add KG entries to elasticsearch
        """
        ...
    
    def search(self, query, *args, **kwargs):
        ...
```

### Crawler

Crawlers are responsible for aggregating data from some source, 
and performing some set of transformations on them to assemble a knowledge graph.

```python
class Crawler:
    
    def crawl(self):
        ...
```

### Indexer

### Parser

Parsers are responsible for transforming data from some source into a set of Indexables, 
which can be DugElements or DugConcepts.

```python

```

### Annotator

### Tranqlizer

### 
