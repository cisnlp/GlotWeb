import csv
import os
import yaml
import json
from typing import List, Dict, Any
from tqdm import tqdm

# Load configuration from a YAML file
def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)


def create_csv(code_list, formatted_output_path, text_files_path, meta_data_path):
    """
    Creates a CSV file containing data extracted from JSON and text files.
    
    Args:
        code_list (list): List of codes to process.
        formatted_output_path (str): Path where formatted JSON files are stored.
        text_files_path (str): Path where text files are stored.
        meta_data_path (str): Path where metadata JSON files are stored.
    """
    # Define the CSV column names
    columns = ['alpha_3_code','language_name', 'num_speakers', 'family', 'madlad', 'flores', 'glot500', 'text_len', 'active_seed_urls', 'acquired_urls', 'newly_discovered_urls']
    output_csv_path = 'collected_language_data.csv'
    
    # Open the CSV file for writing
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()  # Write the header row
        
        # Process each code
        for code in code_list:
            row = {}
            
            # Read the JSON file for the current code
            json_file_path = os.path.join(formatted_output_path, f"{code}.json")
            with open(json_file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
            
            # Populate the CSV row with data
            row['alpha_3_code'] = code
            row['language_name'] = data.get('Language Name', '')  
            row['num_speakers'] = data.get('Number of Speakers', '')  
            row['family'] = data.get('Family','')
            row['madlad'] = data.get('Supported by allenai/MADLAD-400', '') 
            row['flores'] = data.get('Supported by facebook/flores', '')  
            row['glot500'] = data.get('Supported by cis-lmu/Glot500','')
            
            # Read the text file for the current code
            text_file_path = os.path.join(text_files_path, f"{code}.txt")
            with open(text_file_path, 'r', encoding='utf-8') as text_file:
                text_content = text_file.read()
            row['text_len'] = len(text_content)
            
            # Read the metadata JSON file for the current code
            meta_data_file_path = os.path.join(meta_data_path, f"{code}_meta_data.json")
            with open(meta_data_file_path, 'r', encoding='utf-8') as meta_data_file:
                meta_data = json.load(meta_data_file)
            
            # Populate the CSV row with metadata
            row['active_seed_urls'] = meta_data.get('active_seed_urls_len', '')  
            row['acquired_urls'] = meta_data.get('filtered_links_len', '')
            row['newly_discovered_urls'] = meta_data.get('unique_links_len', '')  
            
            # Write the row to the CSV
            writer.writerow(row)
    
    print(f"CSV saved to {output_csv_path}")

if __name__ == "__main__":
    config = load_config('config.yaml')
    formatted_output_path = config['output']['formated_directory']
    text_files_path = config['output']['text_files_directory']
    meta_data_path = os.path.join(config['output']['directory'], "meta_data")
    
    code = config['language_detector']['desired_language']
    # Determine input labels
    if config['batch_processing']['enabled']:
        code_list = config['batch_processing']['input_labels']
    else:
        code_list = [code]
    
    create_csv(code_list,formatted_output_path,text_files_path,meta_data_path)
    
