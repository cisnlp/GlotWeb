import yaml
import os
import re
import requests
from urllib.parse import urljoin, urlparse
import json
from typing import List, Dict, Any
from tqdm import tqdm

def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)

config = load_config('config.yaml')

def remove_entries_with_domains(final_list):
        with open(config['domain_file'], 'r') as f:
            domains = [line.strip() for line in f.readlines()]

        filtered_list = [
            entry for entry in final_list 
            if 'link' in entry and not any(domain in entry['link'] for domain in domains)
        ]
        
        return filtered_list

def load_crawled_output(code: str, data_dir: str) -> List[Dict[str, Any]]:
    """Load crawled output JSON for a given code."""
    file_path = os.path.join(data_dir, f"{code}_crawled_output.json")
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def save_to_json(data: List[Dict[str, Any]], filename: str):
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        print(f"Successfully saved data to {filename}")
    except Exception as e:
        print(f"Error saving to {filename}: {e}")
    

def main():
    config = load_config('config.yaml')
    crawled_output_dir = config['output']['directory']
    code = config['language_detector']['desired_language']

    # Determine input labels
    if config['batch_processing']['enabled']:
        input_labels = config['batch_processing']['input_labels']
    else:
        input_labels = [code]

    for input_label in tqdm(input_labels, desc="Processing input labels"):
        print(f"Processing {input_label}")
        data =  load_crawled_output(input_label,crawled_output_dir)
        data = remove_entries_with_domains(data)
        output_file = os.path.join(config['output']['directory'], 
                              config['output']['output_file_name'].format(language=input_label))
        save_to_json(data, output_file)

if __name__ == "__main__":
    main()
