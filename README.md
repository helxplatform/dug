# Helium Semantic Search POC

## Prerequisites

* Python 3.7.x

## Configure
```
python3.7 -m venv search
pip install -r requiements.txt
```

## Run
```
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" elasticsearch:7.5.2
python search.py --crawl
python search.py --index
python search.py --query coug
```
