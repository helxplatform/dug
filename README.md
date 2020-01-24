# Helium Semantic Search POC

## Prerequisites

* Elasticsearch 7.5.2
* Java 1.8.x
* Python 3.7.x

## Configure
```
python3.7 -m venv search
pip install -r requiements.txt
```

## Run
```
python search.py --crawl
python search.py --index
python search.py --query coug
```
