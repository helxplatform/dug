import requests
import json
import pandas as pd
import sys
import os
from os.path import exists
import subprocess
from dug.core.search import Search
from dug.config import Config
from tabulate import tabulate

# Creating a function which will remove extra leading
# and tailing whitespace from the data.
# pass dataframe as a parameter here
# Lifted shamelessly from 
#
#    https://www.geeksforgeeks.org/pandas-strip-whitespace-from-entire-dataframe/
def whitespace_remover(dataframe):
   
    # iterating over the columns
    for i in dataframe.columns:
         
        # checking datatype of each columns
        if dataframe[i].dtype == 'object':
             
            # applying strip function on column
            dataframe[i] = dataframe[i].map(str.strip)
        else:
             
            # if condn. is False then it will do nothing.
            pass

# First arg is the file name, second arg is the output dir
fileName = sys.argv[1]
outDir = sys.argv[2]
outFile = outDir + "/" + fileName

dirList = []
dirList.append('/Users/howard1/repos/prototypes/results/right-subclass/')
dirList.append('/Users/howard1/repos/prototypes/results/left-subclass/')
dirList.append('/Users/howard1/repos/prototypes/results/one-hop/')
dirList.append('/Users/howard1/repos/prototypes/results/two-hop/')

frames = []
allFrames = pd.DataFrame()
firstFrame = True

for dir in dirList:
  # build the file name
  thisFile = dir + fileName

  # Next check if the file is there. They won't always be
  if (exists(thisFile)):
     # These are tab delimited file, so read them into a data frame
     # with the appropriate call
     print(f"reading {thisFile}")
     thisFrame = pd.read_csv(thisFile, sep = '\t', header = 0)
     thisFrame.columns = thisFrame.columns.str.strip()
     thisFrame.fillna('', inplace=True)
     whitespace_remover(thisFrame)
     #print(f"thisFrame")
     print(tabulate(thisFrame, tablefmt = "tsv"))
     print(f"firstFrame is {firstFrame}")
     if (firstFrame):
        firstFrame = False
        allFrames = thisFrame
        for col in allFrames.columns:
           print(col)
     else:
        print(f"columns from allFrames")
        for col in allFrames.columns:
           print(col)

        print(f"deleting Current from {thisFile}")
        #thisFrame.drop('Current', axis = 1)
        del thisFrame['Current']
        print(f"thisFrame after deleting current")
        print(tabulate(thisFrame, tablefmt = "tsv"))
        print(f"columns from thisFrame")
        for col in thisFrame.columns:
           print(col)

        print(f"merging frames from {thisFile}")
        allFrames = pd.merge(allFrames, thisFrame, on = "Terms", how = "outer")
        allFrames.columns = allFrames.columns.str.strip()
        print(f"columns from allFrames after merge")
        intermediateCols = []
        for col in allFrames.columns:
           print(col)
           intermediateCols.append(col)

        print(f"intermediate allFrames  after merging {thisFile}")
        print(tabulate(allFrames, headers = intermediateCols, tablefmt = "tsv"))
     print(f"firstFrame 2 is {firstFrame}")
     #frames.append(thisFrame)

#allFrames = pd.concat(frames)     
#allFrames.fillna('', inplace=True)

#print(json.dumps(result, indent=4))

colArray = []
for col in allFrames.columns:
  colArray.append(col)
with open(outFile, 'w') as theFile:
    sys.stdout = theFile # Change the standard output to the file we created.
    #print(df.to_string()) 
    #print(tabulate(df, headers = ["Terms", "Current", "Right", "Left", "One Hope", "Two Hop"], tablefmt = "tsv")) 
    allFrames.fillna('', inplace=True)
    print(tabulate(allFrames, headers = colArray,tablefmt = "tsv")) 
