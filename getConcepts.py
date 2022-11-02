import requests
import json
import pandas as pd
import sys
import os
import subprocess
from dug.core.search import Search
from dug.config import Config

theSearch = Search(Config.from_env())

# First arg is the concept, second is the output file
concept = sys.argv[1]
outputFile = sys.argv[2]
url = 'https://helx-howard.apps.renci.org/search-api/search'
headers = {'content-type': 'application/json'}
body = """{"index": "concepts_index", "query": "CONCEPT", "offset": 0, "size": 1000}"""
body = body.replace("CONCEPT", concept)

req = requests.post(url, headers=headers, data=body)

theJson = json.loads(req.text)
theHits = theJson['result']['hits']['hits']

data = {}

# Set up the dict for the results of the current dug2
current={}
for thisHit in theHits:
  thisId = thisHit['_source']['id']
  thisName = thisHit['_source']['name']
  current[thisId] = thisName

data['Current'] = current

protoResults = theSearch.search_concepts("one", concept)
protoHits = protoResults['result']['hits']['hits']
proto = {}
for thisProtoHit in protoHits:
  protoId = thisProtoHit['_source']['_id']
  protoName = thisProtoHit['_source']['name']
  proto[protoId] = protoName

data['Proto'] = proto
#print(json.dumps(result, indent=4))

with open(outputFile, 'w') as theFile:
    sys.stdout = theFile # Change the standard output to the file we created.
    df = pd.DataFrame(data)
    df.fillna('', inplace=True)
    df.sort_index()
    print(df.to_string()) 
