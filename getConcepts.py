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
outputDir = sys.argv[2]
url = 'https://helx-howard.apps.renci.org/search-api/search'
headers = {'content-type': 'application/json'}
body = """{"index": "concepts_index", "query": "CONCEPT", "offset": 0, "size": 1000}"""
body = body.replace("CONCEPT", concept)

req = requests.post(url, headers=headers, data=body)

theJson = json.loads(req.text)
theHits = {}

total_items = theJson['result']['total_items']
if total_items > 0 :
   theHits = theJson['result']['hits']['hits']

data = {}

# Set up the dict for the results of the current dug2
current={}
for thisHit in theHits:
  thisId = thisHit['_source']['id'].strip()
  thisName = thisHit['_source']['name']
  if thisName == "":
     thisName = "None"
  current[thisId] = thisName.strip()

data['Current'] = current

protoResults = theSearch.search_concepts("one", concept)
query = protoResults['query']
query = query.replace(' ', '_')
concept=protoResults['concept']
outputFile = outputDir + "/" + query + "-" + concept

print(f"user query {protoResults['query']}")
print(f"concept {protoResults['concept']}")
protoHits = protoResults['result']['hits']['hits']
proto = {}
for thisProtoHit in protoHits:
  protoId = thisProtoHit['_source']['_id'].strip()
  protoName = thisProtoHit['_source']['name'].strip()
  if protoName == "":
    protoName = 'None'
  proto[protoId] = protoName[:70]

data['Proto'] = proto
#print(json.dumps(result, indent=4))

with open(outputFile, 'w') as theFile:
    sys.stdout = theFile # Change the standard output to the file we created.
    df = pd.DataFrame(data)
    df.fillna('', inplace=True)
    #df = df.sort_index(ascending = True)
    print(df.to_string()) 
