from fastapi import FastAPI, HTTPException
import pandas as pd
from collections import defaultdict
import os
from typing import List, Dict, Any

app = FastAPI()

# Path to the CSV file
CSV_PATH = os.environ.get("CSV_PATH", "")

# Read and process CSV data once at startup
def load_data():
    # Read CSV file
    df = pd.read_csv(CSV_PATH)
    
    # Replace NaN values with None
    df = df.fillna("")
    
  
    programs = defaultdict(list)
    program_descriptions = {}
    
    for _, row in df.iterrows():
        program = row['Program']
        study_name = row['Study Name']
        collection_id = row['Accession']
        description = row.get('Description', "")  # This will be one line description that NHLBI will be share that will appear below the program name on program search funtionality page.
        # Extract base accession for URL
        accession_base = collection_id.split('.c')[0] if '.c' in collection_id else collection_id
        collection_action = f"https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/study.cgi?study_id={accession_base}"
        
        # Add study to its program
        programs[program].append({
            "collection_id": collection_id,
            "collection_action": collection_action,
            "collection_name": study_name
        })
        
        # Store description for each program
        if program not in program_descriptions and description:
            program_descriptions[program] = description
    
    # Create program summary list
    program_summary = []
    for program_name, studies in programs.items():
        program_summary.append({
            "key": program_name,
            "doc_count": len(studies),
            "No_of_studies": {"value": 1},
            "description": program_descriptions.get(program_name, ""),
            "parent_program": [""]
        })
    
    return programs, program_summary

# Load data at startup
programs_dict, programs_summary = load_data()

@app.get("/programs")
def list_programs():
    """List all program names with statistics"""
    return {"result": programs_summary}

@app.get("/program/{program_name}")
def search_program(program_name: str):
    """Get all studies for a specific program"""
    if program_name not in programs_dict:
        raise HTTPException(status_code=404, detail=f"Program '{program_name}' not found")
    
    return {
        "message": "Search result",
        "result": programs_dict[program_name],
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)