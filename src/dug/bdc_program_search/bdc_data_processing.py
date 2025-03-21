import requests
import os
import csv
import json
import logging
import sys
import urllib.parse
import re
from collections import defaultdict, Counter
from datetime import datetime

class BDCDataProcessor:
    def __init__(self, base_dir="data"):
        self.base_dir = base_dir
        self.bdc_dir = os.path.join(base_dir, "bdc_studies")
        self.gen3_dir = os.path.join(base_dir, "gen3_md")
        
        for directory in [self.base_dir, self.bdc_dir, self.gen3_dir]:
            os.makedirs(directory, exist_ok=True)
        
        self.setup_logging()
        
        self.bdc_studies_csv = os.path.join(self.bdc_dir, "all_studies.csv")
        self.bdc_program_log = os.path.join(self.bdc_dir, "program_analysis.log")
        
        self.gen3_raw_csv = os.path.join(self.gen3_dir, "gen3_studies_raw.csv")
        self.gen3_filtered_csv = os.path.join(self.gen3_dir, "gen3_studies_filtered.csv")
        self.gen3_log_file = os.path.join(self.gen3_dir, "gen3_processing.log")
        self.missing_studies_log = os.path.join(self.gen3_dir, "missing_studies.log")
        
        self.bdc_base_url = "https://search-dev.biodatacatalyst.renci.org/search-api"
        self.gen3_base_url = "https://gen3.biodatacatalyst.nhlbi.nih.gov/"
        self.gen3_download_limit = 50
    
    def setup_logging(self):
        self.log_file = os.path.join(self.base_dir, "data_pipeline.log")
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=logging_format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    # BDC API Functions
    def fetch_program_list(self):
        program_list_url = f"{self.bdc_base_url}/program_list"
        response = requests.get(program_list_url)
        return response.json().get("result", [])

    def fetch_program_studies(self, program_name):
        search_program_url = f"{self.bdc_base_url}/search_program"
        params = {"program_name": program_name}
        response = requests.get(search_program_url, params=params)
        return response.json().get("result", [])

    def process_bdc_data(self, show_detailed_studies=False):
        programs = self.fetch_program_list()
        
        program_descriptions = {}
        for program in programs:
            program_descriptions[program["key"]] = program.get("description", "")
        
        with open(self.bdc_studies_csv, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Accession', 'Study Name', 'Program', 'Description'])
        
        with open(self.bdc_program_log, 'w', encoding='utf-8') as logfile:
            logfile.write("=== Program Analysis Summary ===\n\n")
            
            total_studies = 0
            
            for program in programs:
                program_name = program["key"]
                studies = self.fetch_program_studies(program_name)
                study_count = len(studies)
                total_studies += study_count
                
                program_description = program.get("description", "")
                logfile.write(f"Program: {program_name}\n")
                logfile.write(f"Description: {program_description}\n")
                logfile.write(f"Number of Studies: {study_count}\n")
                
                if study_count > 0 and show_detailed_studies:
                    logfile.write("Accession IDs:\n")
                    for study in studies:
                        logfile.write(f"  - {study['collection_id']}\n")
                
                logfile.write("\n" + "="*50 + "\n\n")
                
                with open(self.bdc_studies_csv, 'a', newline='', encoding='utf-8') as csvfile:
                    csvwriter = csv.writer(csvfile)
                    for study in studies:
                        csvwriter.writerow([
                            study.get('collection_id', 'N/A'),
                            study.get('collection_name', 'N/A'),
                            program_name,
                            program_descriptions.get(program_name, "")
                        ])
            
            logfile.write(f"Total Programs Analyzed: {len(programs)}\n")
            logfile.write(f"Total Studies Found: {total_studies}\n")
        
        return self.bdc_studies_csv
    
    # Gen3 API Functions
    def download_gen3_list(self, input_url):
        complete_list = []
        offset = 0
        
        while True:
            url = input_url + f"&limit={self.gen3_download_limit}&offset={offset}"
            
            try:
                partial_list_response = requests.get(url)
                partial_list_response.raise_for_status()
                
                partial_list = partial_list_response.json()
                complete_list.extend(partial_list)
                
                if len(partial_list) < self.gen3_download_limit:
                    break
                    
                offset += self.gen3_download_limit
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error downloading from Gen3: {e}")
                raise
        
        return complete_list

    def download_gen3_raw_data(self):
        mds_discovery_metadata_url = urllib.parse.urljoin(
            self.gen3_base_url,
            f'/mds/metadata?_guid_type=discovery_metadata'
        )
        
        discovery_list = self.download_gen3_list(mds_discovery_metadata_url)
        sorted_study_ids = sorted(discovery_list)
        
        with open(self.gen3_raw_csv, 'w', newline='') as csvfile:
            csv_writer = csv.DictWriter(csvfile, fieldnames=[
                'Accession', 'Study Name', 'Program', 'Description'
            ])
            csv_writer.writeheader()
            
            for study_id in sorted_study_ids:
                study_name = ''
                program_names = []
                description = ''
                
                url = urllib.parse.urljoin(self.gen3_base_url, f'/mds/metadata/{study_id}')
                try:
                    study_info_response = requests.get(url)
                    study_info_response.raise_for_status()
                    study_info = study_info_response.json()
                    
                    if 'gen3_discovery' in study_info:
                        gen3_discovery = study_info['gen3_discovery']
                        
                        if 'full_name' in gen3_discovery:
                            study_name = gen3_discovery['full_name']
                        elif 'name' in gen3_discovery:
                            study_name = gen3_discovery['name']
                        elif 'short_name' in gen3_discovery:
                            study_name = gen3_discovery['short_name']
                        else:
                            study_name = '(no name)'
                        
                        try:
                            if 'authz' in gen3_discovery:
                                match = re.fullmatch(r'^/programs/(.*)/projects/(.*)$', gen3_discovery['authz'])
                                if match:
                                    program_names.append(match.group(1))
                        except Exception as e:
                            pass

                        description = gen3_discovery.get('study_description', '')
                    
                    csv_writer.writerow({
                        'Accession': study_id,
                        'Study Name': study_name,
                        'Description': "",
                        'Program': '|'.join(sorted(set(filter(None, program_names)))),
                    })
                    
                except requests.exceptions.RequestException as e:
                    self.logger.error(f"Error processing study {study_id}: {e}")
                    continue
        
        return self.gen3_raw_csv
    
    def filter_gen3_studies(self):
        total_studies = 0
        valid_studies = 0
        skipped_studies = 0
        
        try:
            with open(self.gen3_raw_csv, 'r', encoding='utf-8') as infile, \
                 open(self.gen3_filtered_csv, 'w', newline='', encoding='utf-8') as outfile:
                
                reader = csv.DictReader(infile)
                writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                writer.writeheader()
                
                for row in reader:
                    total_studies += 1
                    is_valid, invalid_reason = self.validate_gen3_study(row)
                    
                    if is_valid:
                        writer.writerow(row)
                        valid_studies += 1
                    else:
                        skipped_studies += 1
            
        except Exception as e:
            self.logger.error(f"An error occurred during Gen3 filtering: {str(e)}")
            raise
            
        return self.gen3_filtered_csv

    def validate_gen3_study(self, row):
        required_fields = ['Accession', 'Study Name', 'Program']
        missing_fields = []
        
        for field in required_fields:
            if not row.get(field) or row[field].strip() == '':
                missing_fields.append(field)
        
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        return True, None
    
    def process_gen3_data(self):
        self.download_gen3_raw_data()
        self.filter_gen3_studies()
        return self.gen3_filtered_csv
    
    # Data Merge Functions
    def merge_csv_files(self, old_csv_path=None, new_csv_path=None, output_csv_path=None):
        old_csv_path = old_csv_path or self.bdc_studies_csv
        new_csv_path = new_csv_path or self.gen3_filtered_csv
        output_csv_path = output_csv_path or new_csv_path
        
        old_data = {}
        old_accessions = set()
        
        with open(old_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            header = next(reader)
            accession_index = header.index('Accession')
            program_index = header.index('Program')
            description_index = header.index('Description')
            
            for row in reader:
                if row and len(row) > max(accession_index, program_index, description_index):
                    full_accession = row[accession_index]
                    
                    if full_accession.startswith('phs'):
                        base_accession = full_accession.split('.')[0]
                    else:
                        base_accession = full_accession
                        
                    program = row[program_index]
                    description = row[description_index]
                    old_data[base_accession] = (program, description, full_accession)
                    old_accessions.add(base_accession)
        
        updated_rows = []
        new_accessions = set()
        
        with open(new_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            updated_rows.append(header)
            
            new_accession_index = header.index('Accession')
            new_program_index = header.index('Program')
            new_description_index = header.index('Description')
            
            for row in reader:
                if not row or len(row) <= max(new_accession_index, new_program_index, new_description_index):
                    continue
                    
                full_accession = row[new_accession_index]
                
                if full_accession.startswith('phs'):
                    base_accession = full_accession.split('.')[0]
                else:
                    base_accession = full_accession
                    
                new_accessions.add(base_accession)
                
                if base_accession in old_data:
                    row[new_program_index] = old_data[base_accession][0]
                    row[new_description_index] = old_data[base_accession][1]
                
                updated_rows.append(row)
        
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(updated_rows)
        
        missing_studies = old_accessions - new_accessions
        if missing_studies:
            with open(self.missing_studies_log, 'w', encoding='utf-8') as logfile:
                logfile.write(f"Studies in old CSV but not in new CSV ({len(missing_studies)} total):\n")
                for base_accession in sorted(missing_studies):
                    program, description, full_accession = old_data[base_accession]
                    logfile.write(f"Base Accession: {base_accession}, Full Accession: {full_accession}, Program: {program}, Description: {description}\n")
        
        return output_csv_path
    
    def run_full_pipeline(self):
        self.process_bdc_data()  #get the currrent data from the bdc portal
        self.process_gen3_data() #get the current data from gen3 and filter that has required information
        self.merge_csv_files()   #the output csv will have the decriptions and program names from the bdc portal 
                                 #for all studies that are in csv from gen3 and bdc. The new studies will have 
        return self.gen3_filtered_csv


def main():
    processor = BDCDataProcessor()
    final_path = processor.run_full_pipeline()
    print(f"Processing completed successfully!")
    print(f"Final data file: {final_path}")


if __name__ == "__main__":
    main()